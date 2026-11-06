Using your own domain
=====================

You do not need a domain
------------------------

Alexa never shows these URLs to anyone. The only clients are
Amazon's servers and your Echo. There is no branding value and
nobody types them. A domain buys you nothing here except a
stable hostname, and Tailscale Funnel already gives you one
free. Read the warning below before using a family domain.


Warning about sdpmss.com, or any business domain
------------------------------------------------

Cloudflare retired the old Section 2.8 but moved the rule into
their CDN specific Service Specific Terms. The current rule:
you may serve video and other large files through the CDN only
if that content is hosted on a Cloudflare service such as
Stream, Images or R2. Large files hosted elsewhere stay
restricted.

Audio served from a phone in your house is hosted elsewhere,
and it is the bulk of this traffic.

The old escape hatch was to grey cloud the subdomain, because
those restrictions did not apply to non proxied subdomains.
That hatch is closed here: Cloudflare Tunnel requires a proxied
CNAME to <UUID>.cfargotunnel.com, so with a tunnel you are
always on the CDN.

At roughly 1 GB a day, enforcement is unlikely. The problem is
the blast radius. Any action lands on the Cloudflare account
that also fronts the live business site. Buying a separate
cheap domain does not help either, because the CDN terms apply
per account.

Second, smaller issue: if the business site sets cookies scoped
to Domain=.sdpmss.com, any browser logged into it will send
those cookies to your phone when it hits your subdomain.

Recommendation: keep the business domain out of this. Use
Tailscale Funnel, or the Oracle relay below.


Option A, Tailscale Funnel, no domain
-------------------------------------

See docs/SETUP-MOBILE.md step 5. Free, nothing to buy, no CDN
terms, nothing shared with the business.


Option B, Oracle Always Free relay, no Cloudflare
-------------------------------------------------

Use this if Funnel will not issue a cert inside Termux. It
keeps Cloudflare out of the path entirely.

  Echo -> alexa-music.duckdns.org   A record to the Oracle VM
       -> nginx, Let's Encrypt cert
       -> WireGuard tunnel
       -> your phone, which does the yt-dlp work on your
          home IP so the stream URL binding still holds

Oracle's always free tier includes a VM and 10 TB a month of
egress. DuckDNS hostnames are free. The VM is only a relay, so
extraction stays on the phone and you keep the residential IP
advantage.

nginx needs these for Alexa and for seeking to work:

  proxy_http_version 1.1;
  proxy_buffering off;
  proxy_request_buffering off;
  proxy_set_header Host $host;
  client_max_body_size 1m;
  proxy_read_timeout 300s;

Set public_hosts in the console to your DuckDNS hostname.


Option C, the subdomain anyway
------------------------------

If you decide the risk is acceptable, this is the least bad
way to do it.

1. In Cloudflare DNS for sdpmss.com, create the record BY HAND:

     type    CNAME
     name    music
     target  <TUNNEL-UUID>.cfargotunnel.com
     proxy   on

   Create it in the dashboard. Do NOT give cloudflared an API
   token with DNS write permission on the zone. Use a scoped
   tunnel token only, so a compromised phone cannot touch the
   business records.

2. Install cloudflared, ARM64 build, into Termux.

3. Create the tunnel on a machine you trust, not the phone,
   and copy only the tunnel credentials over.

4. Write $HOME/.ytalexa/cloudflared.yml:

     tunnel: <TUNNEL-UUID>
     credentials-file: /data/data/com.termux/files/home/.ytalexa/cf.json
     ingress:
       - hostname: music.sdpmss.com
         path: ^/alexa$
         service: http://127.0.0.1:8080
       - hostname: music.sdpmss.com
         path: ^/audio/.*$
         service: http://127.0.0.1:8080
       - service: http_status:404

   The trailing 404 rule is what keeps /ui and /api off the
   internet. Without it the console is exposed. Do not omit it.

5. Start it:

     bash bin/tunnel.sh cloudflare

6. In the console Config tab, set public_hosts to:

     music.sdpmss.com

   The server then refuses any Alexa request arriving with a
   different Host header.

7. Verify the console is NOT reachable:

     curl -i https://music.sdpmss.com/ui/
     curl -i https://music.sdpmss.com/api/status

   Both must return 404 from Cloudflare. If either returns
   anything else, your ingress rules are wrong. Fix that
   before going further.


Switching later
---------------

Only two things change: which tunnel runs, and public_hosts in
the console. The application code is identical either way, so
you can move between options whenever you like.
