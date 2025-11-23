#!/usr/bin/env node

/**
 * Policy Documents MCP Server
 * Indexes text policy documents and provides semantic search capabilities
 * Now includes HTTP API for easy integration with web applications
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import * as fs from "fs";
import * as path from "path";
import express from "express";
import cors from "cors";

/**
 * Type definitions
 */
interface DocumentSection {
  documentName: string;
  sectionId: string;
  page: number;
  text: string;
  startIndex: number;
  endIndex: number;
}

interface PolicyDocument {
  name: string;
  path: string;
  totalPages: number;
  sections: DocumentSection[];
  fullText: string;
}

/**
 * Policy Documents Server Class
 */
class PolicyDocumentsServer {
  public server: Server;  // Made public for external MCP connection
  private documents: Map<string, PolicyDocument> = new Map();
  private documentsPath: string;

  constructor() {
    this.server = new Server(
      {
        name: "policy-docs-server",
        version: "1.0.0",
      },
      {
        capabilities: {
          resources: {},
          tools: {},
        },
      }
    );

    // Path to documents folder (absolute path to ensure it works from any working directory)
    // Get the directory where the compiled JS file is located
    const fileUrl = new URL(import.meta.url);
    let serverDir = fileUrl.pathname;
    // Remove leading slash on Windows (e.g., /C:/... becomes C:/...)
    if (process.platform === 'win32' && serverDir.startsWith('/')) {
      serverDir = serverDir.substring(1);
    }
    serverDir = path.dirname(serverDir);
    this.documentsPath = path.join(serverDir, "..", "..", "documents");

    this.setupHandlers();
  }

  /**
   * Initialize: Load and index all text documents
   */
  async initialize() {
    console.error("[Policy Docs] Initializing server...");
    console.error(`[Policy Docs] Documents path: ${this.documentsPath}`);

    try {
      await this.loadAllDocuments();
      console.error(`[Policy Docs] Successfully loaded ${this.documents.size} documents`);
    } catch (error) {
      console.error("[Policy Docs] Error loading documents:", error);
      throw error;
    }
  }

  /**
   * Load all text documents from the documents folder
   */
  private async loadAllDocuments() {
    if (!fs.existsSync(this.documentsPath)) {
      throw new Error(`Documents directory not found: ${this.documentsPath}`);
    }

    const files = fs.readdirSync(this.documentsPath);
    const txtFiles = files.filter(f => f.toLowerCase().endsWith(".txt"));

    console.error(`[Policy Docs] Found ${txtFiles.length} text files`);

    for (const file of txtFiles) {
      try {
        await this.loadDocument(file);
      } catch (error) {
        console.error(`[Policy Docs] Error loading ${file}:`, error);
      }
    }
  }

  /**
   * Load and process a single text document
   */
  private async loadDocument(filename: string) {
    const filePath = path.join(this.documentsPath, filename);
    console.error(`[Policy Docs] Loading: ${filename}`);

    // Read text file
    const fullText = fs.readFileSync(filePath, 'utf-8');
    
    // For text files, we don't have actual pages, so we'll use section count as a proxy
    // This keeps the interface consistent
    const estimatedPages = 1; // Text files are treated as single-page documents
    
    // Split text into sections
    const sections = this.createSections(filename, fullText, estimatedPages);

    const document: PolicyDocument = {
      name: filename,
      path: filePath,
      totalPages: estimatedPages,
      sections: sections,
      fullText: fullText,
    };

    this.documents.set(filename, document);
    console.error(`[Policy Docs] Loaded ${filename}: ${sections.length} sections (${fullText.length} characters)`);
  }

  /**
   * Create semantically meaningful sections from document text
   * First checks for explicit section markers (===== SECTION X =====)
   * Falls back to sentence-based chunking if no markers found
   */
  private createSections(
    documentName: string,
    fullText: string,
    totalPages: number
  ): DocumentSection[] {
    // Try to split by explicit section markers first
    const sectionMarkerPattern = /={5,}\s*SECTION\s+\d+:[^=]+={5,}/gi;
    const markerMatches = Array.from(fullText.matchAll(sectionMarkerPattern));
    
    if (markerMatches.length > 0) {
      // Document has explicit section markers - use them!
      return this.createSectionsFromMarkers(documentName, fullText, markerMatches, totalPages);
    } else {
      // Fall back to sentence-based chunking
      return this.createSectionsFromSentences(documentName, fullText, totalPages);
    }
  }

  /**
   * Create sections based on explicit ===== SECTION X: NAME ===== markers
   */
  private createSectionsFromMarkers(
    documentName: string,
    fullText: string,
    markerMatches: RegExpMatchArray[],
    totalPages: number
  ): DocumentSection[] {
    const sections: DocumentSection[] = [];
    const maxSectionSize = 1500; // If section > 1500 chars, consider chunking
    
    for (let i = 0; i < markerMatches.length; i++) {
      const match = markerMatches[i];
      const startIndex = match.index!;
      const endIndex = i < markerMatches.length - 1 ? markerMatches[i + 1].index! : fullText.length;
      const sectionText = fullText.substring(startIndex, endIndex).trim();
      
      if (sectionText.length <= maxSectionSize) {
        // Section is reasonable size - keep it as one section
        sections.push({
          documentName,
          sectionId: `${documentName}-section-${sections.length}`,
          page: 1,
          text: sectionText,
          startIndex: startIndex,
          endIndex: endIndex
        });
      } else {
        // Section is large - chunk it further while preserving section header
        const headerMatch = sectionText.match(/^={5,}[^=]+={5,}/);
        const header = headerMatch ? headerMatch[0] : '';
        const content = header ? sectionText.substring(header.length).trim() : sectionText;
        
        // Chunk the content
        const chunks = this.chunkLargeSection(content, 800);
        for (let j = 0; j < chunks.length; j++) {
          sections.push({
            documentName,
            sectionId: `${documentName}-section-${sections.length}`,
            page: 1,
            text: j === 0 ? `${header}\n\n${chunks[j]}` : chunks[j],
            startIndex: startIndex,
            endIndex: endIndex
          });
        }
      }
    }
    
    return sections;
  }

  /**
   * Chunk a large section into smaller pieces
   */
  private chunkLargeSection(text: string, targetSize: number): string[] {
    const chunks: string[] = [];
    const paragraphs = text.split(/\n\n+/);
    
    let currentChunk = '';
    for (const para of paragraphs) {
      if (currentChunk.length + para.length <= targetSize) {
        currentChunk += (currentChunk ? '\n\n' : '') + para;
      } else {
        if (currentChunk) {
          chunks.push(currentChunk.trim());
        }
        currentChunk = para;
      }
    }
    
    if (currentChunk.trim()) {
      chunks.push(currentChunk.trim());
    }
    
    return chunks.length > 0 ? chunks : [text];
  }

  /**
   * Create sections using sentence-based chunking (fallback method)
   */
  private createSectionsFromSentences(
    documentName: string,
    fullText: string,
    totalPages: number
  ): DocumentSection[] {
    const sections: DocumentSection[] = [];
    const targetChunkSize = 400;
    const maxChunkSize = 600;
    const overlapSize = 50;

    const sentences = fullText.match(/[^.!?]+[.!?]+[\s]*/g) || [fullText];
    
    let currentChunk = '';
    let currentStartIndex = 0;
    let sectionCount = 0;

    for (let i = 0; i < sentences.length; i++) {
      const sentence = sentences[i].trim();
      if (!sentence) continue;

      const isHeading = this.looksLikeHeading(sentence);
      const shouldBreak = this.shouldBreakHere(currentChunk, sentence, isHeading, targetChunkSize, maxChunkSize);

      if (shouldBreak && currentChunk.length > 0) {
        const endIndex = currentStartIndex + currentChunk.length;
        const estimatedPage = Math.ceil((currentStartIndex / fullText.length) * totalPages);

        sections.push({
          documentName,
          sectionId: `${documentName}-section-${sectionCount}`,
          page: estimatedPage,
          text: currentChunk.trim(),
          startIndex: currentStartIndex,
          endIndex: endIndex,
        });

        if (isHeading) {
          currentStartIndex = endIndex;
          currentChunk = sentence;
        } else {
          const overlapText = currentChunk.slice(-overlapSize);
          currentStartIndex = endIndex - overlapSize;
          currentChunk = overlapText + ' ' + sentence;
        }
        sectionCount++;
      } else {
        currentChunk += (currentChunk.length > 0 ? ' ' : '') + sentence;
      }
    }

    if (currentChunk.trim().length > 0) {
      const estimatedPage = Math.ceil((currentStartIndex / fullText.length) * totalPages);
      sections.push({
        documentName,
        sectionId: `${documentName}-section-${sectionCount}`,
        page: estimatedPage,
        text: currentChunk.trim(),
        startIndex: currentStartIndex,
        endIndex: currentStartIndex + currentChunk.length,
      });
    }

    return sections;
  }

  /**
   * Detect if a sentence looks like a heading or section marker
   */
  private looksLikeHeading(sentence: string): boolean {
    const trimmed = sentence.trim();
    
    // Check various heading patterns
    const headingPatterns = [
      /^[A-Z][A-Z\s]{3,}[.:]?\s*$/,              // ALL CAPS HEADING
      /^\d+\.\s+[A-Z]/,                           // 1. Numbered section
      /^[A-Z][^.!?]{5,50}:$/,                     // Title Case Heading:
      /^(Chapter|Section|Part|Article)\s+\d+/i,   // Chapter 1, Section 2, etc.
      /^[IVX]+\.\s+[A-Z]/,                        // Roman numerals: I. II. etc.
      /^\([a-z]\)\s+[A-Z]/,                       // (a) Lettered sections
    ];

    return headingPatterns.some(pattern => pattern.test(trimmed));
  }

  /**
   * Decide whether to break and start a new section
   */
  private shouldBreakHere(
    currentChunk: string,
    nextSentence: string,
    isHeading: boolean,
    targetSize: number,
    maxSize: number
  ): boolean {
    const currentSize = currentChunk.length;
    const nextSize = nextSentence.length;

    // Always break at headings if we have content
    if (isHeading && currentSize > 200) {
      return true;
    }

    // Force break if we're over max size
    if (currentSize + nextSize > maxSize) {
      return true;
    }

    // Break if we're over target size and the next sentence seems like a good break point
    if (currentSize > targetSize) {
      // Good break points: starts with capital, looks like new topic
      const startsNewTopic = /^[A-Z]/.test(nextSentence) && 
                            (nextSentence.length > 50 || isHeading);
      return startsNewTopic;
    }

    return false;
  }

  /**
   * Simple keyword-based search across all documents
   * Returns sections that contain the most query terms
   * Deduplicates results to avoid returning the same section multiple times
   */
  public searchDocuments(query: string, maxResults: number = 10): DocumentSection[] {
    // Normalize query to lowercase and split into terms
    const queryTerms = query.toLowerCase()
      .split(/\s+/)
      .filter(term => term.length > 2); // Ignore very short words

    const scoredSections: Array<{ section: DocumentSection; score: number }> = [];

    // Score each section based on keyword matches
    for (const doc of this.documents.values()) {
      for (const section of doc.sections) {
        const sectionLower = section.text.toLowerCase();
        let score = 0;

        for (const term of queryTerms) {
          // Escape special regex characters
          const escapedTerm = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          
          // Count occurrences of each term
          const matches = (sectionLower.match(new RegExp(escapedTerm, "g")) || []).length;
          score += matches;

          // Bonus for exact phrase match
          if (sectionLower.includes(query.toLowerCase())) {
            score += 5;
          }
        }

        if (score > 0) {
          scoredSections.push({ section, score });
        }
      }
    }

    // Deduplicate by section_id, keeping the highest score for each unique section
    const uniqueSections = new Map<string, { section: DocumentSection; score: number }>();
    
    for (const item of scoredSections) {
      const existing = uniqueSections.get(item.section.sectionId);
      // Keep this section if it doesn't exist yet OR if it has a higher score
      if (!existing || item.score > existing.score) {
        uniqueSections.set(item.section.sectionId, item);
      }
    }

    // Convert back to array, sort by score (descending), and return top results
    const deduplicated = Array.from(uniqueSections.values());
    deduplicated.sort((a, b) => b.score - a.score);
    return deduplicated.slice(0, maxResults).map(s => s.section);
  }

  /**
   * Setup MCP request handlers
   */
  private setupHandlers() {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "search_policies",
            description: "Search across all policy documents for relevant sections",
            inputSchema: {
              type: "object",
              properties: {
                query: {
                  type: "string",
                  description: "Search query (keywords or phrases)",
                },
                max_results: {
                  type: "number",
                  description: "Maximum number of results to return (default: 10)",
                  default: 10,
                },
              },
              required: ["query"],
            },
          },
          {
            name: "list_documents",
            description: "List all available policy documents",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
          {
            name: "get_document_info",
            description: "Get detailed information about a specific document",
            inputSchema: {
              type: "object",
              properties: {
                document_name: {
                  type: "string",
                  description: "Name of the document (e.g., 'GSAS Guide.pdf')",
                },
              },
              required: ["document_name"],
            },
          },
        ],
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case "search_policies": {
            const query = String(args?.query || "");
            const maxResults = Number(args?.max_results || 10);

            if (!query) {
              throw new Error("Query is required");
            }

            const results = this.searchDocuments(query, maxResults);

            return {
              content: [
                {
                  type: "text",
                  text: JSON.stringify(
                    {
                      query: query,
                      results: results.map(r => ({
                        document: r.documentName,
                        section_id: r.sectionId,
                        page: r.page,
                        text: r.text,
                      })),
                      total_results: results.length,
                    },
                    null,
                    2
                  ),
                },
              ],
            };
          }

          case "list_documents": {
            const docList = Array.from(this.documents.values()).map(doc => ({
              name: doc.name,
              pages: doc.totalPages,
              sections: doc.sections.length,
            }));

            return {
              content: [
                {
                  type: "text",
                  text: JSON.stringify(
                    {
                      documents: docList,
                      total: docList.length,
                    },
                    null,
                    2
                  ),
                },
              ],
            };
          }

          case "get_document_info": {
            const documentName = String(args?.document_name || "");
            const doc = this.documents.get(documentName);

            if (!doc) {
              throw new Error(`Document not found: ${documentName}`);
            }

            return {
              content: [
                {
                  type: "text",
                  text: JSON.stringify(
                    {
                      name: doc.name,
                      pages: doc.totalPages,
                      sections: doc.sections.length,
                      preview: doc.fullText.substring(0, 500) + "...",
                    },
                    null,
                    2
                  ),
                },
              ],
            };
          }

          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `Error: ${error instanceof Error ? error.message : String(error)}`,
            },
          ],
          isError: true,
        };
      }
    });

    // List resources (documents as resources)
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      return {
        resources: Array.from(this.documents.values()).map(doc => ({
          uri: `policy://${encodeURIComponent(doc.name)}`,
          name: doc.name,
          mimeType: "application/pdf",
          description: `Policy document with ${doc.totalPages} pages`,
        })),
      };
    });

    // Read resource (get document info)
    this.server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
      const uri = new URL(request.params.uri);
      const docName = decodeURIComponent(uri.hostname);
      const doc = this.documents.get(docName);

      if (!doc) {
        throw new Error(`Document not found: ${docName}`);
      }

      return {
        contents: [
          {
            uri: request.params.uri,
            mimeType: "text/plain",
            text: `Document: ${doc.name}\nPages: ${doc.totalPages}\nSections: ${doc.sections.length}\n\nPreview:\n${doc.fullText.substring(0, 1000)}...`,
          },
        ],
      };
    });

    // Error handling
    this.server.onerror = (error) => console.error("[MCP Error]", error);
    process.on("SIGINT", async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  /**
   * Start the server
   */
  async run() {
    await this.initialize();
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error("[Policy Docs] Server running and ready");
  }
}

// Create and initialize the policy server
const policyServer = new PolicyDocumentsServer();

// Setup HTTP API (before initialization)
const app = express();
app.use(cors());
app.use(express.json());

// Health check endpoint
app.get('/health', (req, res) => {
  const totalSections = Array.from((policyServer as any).documents.values())
    .reduce((sum: number, doc: any) => sum + doc.sections.length, 0);
  
  res.json({
    status: 'ok',
    documents: (policyServer as any).documents.size,
    sections: totalSections
  });
});

// Search endpoint
app.post('/api/search', (req, res) => {
  try {
    const { query, max_results = 10 } = req.body;
    
    if (!query) {
      return res.status(400).json({ error: 'Query is required' });
    }
    
    // Now calling the public method directly
    const results = policyServer.searchDocuments(query, max_results);
    
    res.json({
      query: query,
      results: results.map((r) => ({
        document: r.documentName,
        section_id: r.sectionId,
        page: r.page,
        text: r.text
      })),
      total: results.length
    });
  } catch (error) {
    console.error('[HTTP API] Search error:', error);
    res.status(500).json({ 
      error: error instanceof Error ? error.message : String(error) 
    });
  }
});

// List documents endpoint
app.get('/api/documents', (req, res) => {
  const docs = Array.from((policyServer as any).documents.values()).map((doc: any) => ({
    name: doc.name,
    pages: doc.totalPages,
    sections: doc.sections.length
  }));
  
  res.json({
    documents: docs,
    total: docs.length
  });
});

// Initialize documents (only once!)
await policyServer.initialize();

// Start HTTP server
const HTTP_PORT = process.env.HTTP_PORT || 3000;
app.listen(HTTP_PORT, () => {
  console.error(`[Policy Docs] HTTP API running on http://localhost:${HTTP_PORT}`);
  console.error(`[Policy Docs] Ready to accept requests`);
});

// Also start MCP server for Cline integration (run() will NOT reinitialize now)
// Connect to MCP transport without reinitializing
const transport = new StdioServerTransport();
await policyServer.server.connect(transport);
console.error("[Policy Docs] MCP server connected");
