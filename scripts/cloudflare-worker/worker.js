// Cloudflare Worker: proxy validation submissions to GitHub repository_dispatch
//
// Deploy via Cloudflare Dashboard > Workers > Create Worker
//
// Environment variables (set in Cloudflare dashboard > Worker Settings > Variables):
//   GITHUB_PAT:     fine-grained PAT with actions:write on SimonDedman/elasmo_analyses
//   DISPATCH_TOKEN: shared secret that validators include in their POST body

export default {
  async fetch(request, env) {
    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type',
        },
      });
    }

    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      const body = await request.json();

      // Validate shared token
      if (!body.token || body.token !== env.DISPATCH_TOKEN) {
        return new Response('Unauthorized', { status: 401 });
      }

      if (!body.payload || !body.payload.openalex_id) {
        return new Response('Bad request: missing payload', { status: 400 });
      }

      // Forward to GitHub repository_dispatch
      const response = await fetch(
        'https://api.github.com/repos/SimonDedman/elasmo_analyses/dispatches',
        {
          method: 'POST',
          headers: {
            'Accept': 'application/vnd.github+json',
            'Authorization': 'Bearer ' + env.GITHUB_PAT,
            'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json',
            'User-Agent': 'elasmo-validation-proxy',
          },
          body: JSON.stringify({
            event_type: 'validation-submitted',
            client_payload: body.payload,
          }),
        }
      );

      if (!response.ok) {
        const errText = await response.text();
        console.error('GitHub API error:', response.status, errText);
        return new Response('GitHub API error: ' + response.status, {
          status: 502,
          headers: { 'Access-Control-Allow-Origin': '*' },
        });
      }

      return new Response(JSON.stringify({ ok: true }), {
        headers: {
          'Content-Type': 'application/json',
          'Access-Control-Allow-Origin': '*',
        },
      });
    } catch (err) {
      return new Response('Bad request: ' + err.message, {
        status: 400,
        headers: { 'Access-Control-Allow-Origin': '*' },
      });
    }
  },
};
