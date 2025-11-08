# Policy Query Web Application

Simple web interface for querying Columbia University policy documents using Claude AI and MCP.

## Features

- 🎯 **Simple UI**: Clean, single-page interface
- 🤖 **AI-Powered**: Uses Claude 3.5 Sonnet with MCP tools
- ⚡ **Fast**: Local MCP server for quick searches
- 🎨 **Responsive**: Works on desktop and mobile
- 📊 **Transparent**: Shows which tools were used

## Quick Start

### Prerequisites

1. **Python 3.10+** installed
2. **Anthropic API Key** - Get one from https://console.anthropic.com/

### Setup (5 minutes)

1. **Install dependencies**:
```bash
cd webapp
pip install -r requirements.txt
```

2. **Set your API key**:

**Windows**:
```bash
set ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

**Mac/Linux**:
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

3. **Start the server**:
```bash
python app.py
```

4. **Open your browser**:
```
http://localhost:5000
```

That's it! 🎉

## How to Use

1. **Type your question** in the text box
   - Example: "Can I defend my thesis while on OPT?"
   
2. **Click "Ask Question"** (or press Ctrl+Enter)

3. **Wait for response** (usually 3-10 seconds)

4. **Read the answer** with cited policy rules

## Example Questions

Try these to test the system:

### Basic Queries
- "What are the defense registration requirements?"
- "When must I defend my prospectus?"
- "What is the deadline for MPhil degree?"

### Conflict Resolution
- "I'm a PhD student in Computer Science on F-1 visa. Can I defend while on OPT?"
- "Do SEAS or GSAS rules apply for registration?"
- "What's the difference between prospectus and proposal deadlines?"

### Specific Rules
- "What does rule GSAS:DEFENSE-REG-001 say?"
- "Tell me about ISSO enrollment requirements"

## Architecture

```
User Browser
    ↓ HTTP
Flask Server (app.py)
    ↓ Python import
MCP Server Logic (policy_server/server.py)
    ↓ Reads
Policy Documents (documents/*.txt)
    ↓ Returns excerpts
Flask → Claude API
    ↓ Reasons
Claude → Response
```

## What Gets Sent to Claude API?

### Each Query Sends:
- Your question (~50 tokens)
- Tool definitions (~800 tokens)
- Search results: 5-10 relevant rules (~2,000-3,000 tokens)
- Conflict metadata (~400 tokens)

### Total per query: ~3,000-4,500 tokens

### What DOESN'T get sent:
- ❌ Full policy documents (stay local)
- ❌ All 209 rules (only relevant ones)
- ❌ Any personal data you don't include in your query

## Cost Estimate

Using Claude 3.5 Sonnet:
- **Input**: ~$0.003 per 1K tokens
- **Output**: ~$0.015 per 1K tokens
- **Average cost per query**: $0.03-0.05 (3-5 cents)

For 100 queries: ~$3-5

## Troubleshooting

### Server Won't Start

**Error: "No module named 'flask'"**
```bash
pip install flask anthropic
```

**Error: "ANTHROPIC_API_KEY not set"**
```bash
# Set the environment variable as shown in step 2 above
```

### No Results or Errors

**"Error: Anthropic API key not configured"**
- Make sure you set the `ANTHROPIC_API_KEY` environment variable
- Restart the server after setting it

**"Error calling MCP tool"**
- Make sure the `policy_server/` directory exists
- Ensure `documents/` folder has all 3 .txt files
- Check that `conflicts.json` is in the project root

### Browser Can't Connect

**"This site can't be reached"**
- Make sure the Flask server is running (you should see output in terminal)
- Try `http://127.0.0.1:5000` instead of `localhost`
- Check if another service is using port 5000

## File Structure

```
webapp/
├── app.py                 # Flask backend
├── static/
│   └── index.html        # Frontend UI
├── requirements.txt      # Python dependencies
└── README.md            # This file

Required in parent directory:
├── policy_server/
│   └── server.py         # MCP server logic
├── documents/
│   ├── gsas.txt         # Policy documents
│   ├── isso.txt
│   └── phd_seas.txt
└── conflicts.json       # Conflict metadata
```

## Development

### Adding Features

**To add more example queries**:
Edit `static/index.html`, find the `.example-chips` section, add:
```html
<span class="chip">Your new example</span>
```

**To change styling**:
Edit the `<style>` section in `static/index.html`

**To add API endpoints**:
Add routes in `app.py`:
```python
@app.route('/api/new-endpoint', methods=['POST'])
def new_endpoint():
    # Your code here
    return jsonify({"result": "data"})
```

### Running in Production

For production deployment, use a proper WSGI server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Or deploy to:
- **Heroku**: Add `Procfile` with `web: gunicorn app:app`
- **Railway**: Auto-detects Flask apps
- **Vercel**: Use serverless functions

## Security Notes

### API Key Security
- Never commit your API key to git
- Use environment variables
- In production, use secrets management (e.g., AWS Secrets Manager)

### Rate Limiting
Currently there's no rate limiting. For production, add:
```python
from flask_limiter import Limiter
limiter = Limiter(app, default_limits=["10 per minute"])
```

### CORS
If you need to access this API from another domain:
```python
from flask_cors import CORS
CORS(app)
```

## Performance

### Typical Response Times
- Simple query: 2-4 seconds
- Complex query with conflicts: 4-8 seconds
- Multiple tool uses: 6-12 seconds

### Optimization Tips
1. **Cache common queries**: Add Redis caching
2. **Persistent MCP connection**: Keep server running instead of imports
3. **Async processing**: Use websockets for real-time updates
4. **Index optimization**: Use vector embeddings for better search

## Support

### For issues with:
- **Flask/Python**: Check Flask documentation
- **Claude API**: Check Anthropic documentation
- **MCP Server**: Review `policy_server/README.md`
- **This web app**: Check the code comments in `app.py`

## Next Steps

After verifying it works:
1. ✅ Test with various queries
2. ✅ Verify conflict detection works
3. ✅ Check token usage in Anthropic console
4. 🔄 Gather user feedback
5. 🔄 Add more features based on needs

## License

This is a custom application for Columbia University policy queries.
