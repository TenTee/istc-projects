/** @type {import('next').NextConfig} */

// Démonstration locale (outils/demo/lancer_demo.sh) : l'API Django est servie via le même
// domaine que l'interface (proxy), ce qui évite tout problème de CORS ou de blocage navigateur.
// Sans la variable DEMO_API_PROXY, cette configuration n'a aucun effet.
const demoApi = process.env.DEMO_API_PROXY;

const nextConfig = {
  ...(demoApi
    ? {
        skipTrailingSlashRedirect: true,
        async rewrites() {
          return {
            // « fallback » : les routes Next.js existantes (/api/demo-capture, /api/media-download) restent prioritaires.
            fallback: [
              { source: '/api/:path*/', destination: `${demoApi}/api/:path*/` },
              { source: '/api/:path*', destination: `${demoApi}/api/:path*` },
              { source: '/media/:path*', destination: `${demoApi}/media/:path*` },
            ],
          };
        },
      }
    : {}),
};

export default nextConfig;
