import { Tunnel } from "cloudflared";

console.log("🚀 Creating Cloudflared Tunnel...");

(async function main(port) {
  if (!port) {
    console.error("❗ Usage: node tunnel.js <port>");
    process.exit(1);
  }

  const tunnel = Tunnel.quick(`http://localhost:${port}`);

  // show the URL
  const tunnelUrl = new Promise((resolve) => tunnel.once("url", resolve));
  console.log("🔗 LINK:", await tunnelUrl);

  // wait for connection to be established
  const conn = new Promise((resolve) => tunnel.once("connected", resolve));
  console.log("✅ CONN:", await conn);
})(process.argv[2]);
