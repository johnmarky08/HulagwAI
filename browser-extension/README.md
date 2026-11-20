# HulagwAI Image Scanner — Beta

The HulagwAI Image Scanner is a Chromium desktop extension for scanning a specific image anywhere on the web. It adds no buttons or overlays to webpages: right-click the image you want, choose **Scan image with HulagwAI**, review the confirmation, and explicitly approve the upload.

## Install and pair

1. Download the beta ZIP from HulagwAI's **Extension** page and extract it to a permanent folder.
2. Open `brave://extensions`, `chrome://extensions`, or `edge://extensions`.
3. Turn on **Developer mode**, choose **Load unpacked**, then select the extracted folder containing `manifest.json`.
4. Click the HulagwAI extension icon to open its settings in a browser-anchored popup beside the toolbar action. Enter your HulagwAI site address and choose **Open secure pairing page**. Grant access to that exact HulagwAI origin.
5. Sign in if prompted, copy the one-time pairing code, return to the extension popup, paste it, then choose **Pair extension**. The code expires after three minutes and can only be used once.
6. Leave **Enable right-click scanning** on. On any webpage, right-click an image and choose **Scan image with HulagwAI**.
7. The HulagwAI popup opens from the toolbar icon with a confirmation that previews the selected image. If Chrome blocks the popup from opening automatically, the toolbar icon shows a badge; click the icon to review the request. Grant access to the image host if asked, then choose **Send image for analysis**. No upload occurs before this explicit confirmation.

Settings and scan confirmations both live in the browser action popup; the extension does not open separate windows. A pending scan stays in the popup until you confirm, cancel, or it expires after 10 minutes. The extension keeps no content script running in webpages. It requests permission only for the HulagwAI site during pairing and for the selected image host when you initiate a scan. You can revoke these permissions from the browser's extension settings. The HulagwAI token can be revoked from the extension popup and expires after 30 days.

## What to expect

- Right-click a single image; there are no persistent scan buttons covering Facebook or other pages.
- After you confirm, the extension fetches JPG/JPEG, PNG, or WEBP images up to 5 MB and sends them to HulagwAI.
- The extension popup's **Recent scan activity** shows status, file type/size, and analysis ID. It does not store image bytes, image URLs, or page URLs in the log.
- The selected image is fetched without sending the page's login cookies. Images that require a logged-in session, anti-hotlink headers, or a browser-only `blob:` URL may not be accessible.
- HulagwAI's analysis queue and model service must be running for results to complete.

## Requirements and limitations

- Beta release for Chromium desktop browsers (Brave, Chrome, and Edge); not yet listed in an extension store.
- Requires a HulagwAI account to pair.
- Scans ordinary HTTP/HTTPS image URLs. Some redirects, protected images, SVGs, `data:` URLs, and `blob:` URLs may be unsupported.
- The browser asks you to grant access to the exact origin hosting the selected image. The extension does not request blanket access to all websites.
- Scan requests are always user-initiated from the image context menu, and every upload requires a separate confirmation.

## Maintainer note

After changing extension files or its version, run `npm run extension:package` to regenerate the ZIP served by the download page.

## Troubleshooting

- **No context-menu item:** open the extension popup and turn on **Enable right-click scanning**. Reload the extension in its browser settings if necessary.
- **Permission request declined:** right-click the image again and grant access to its host; permission is limited to that origin.
- **Image could not be fetched:** the image may require a logged-in site session, be protected from extension downloads, or use an unsupported `blob:`/`data:` URL.
- **Upload accepted but still processing:** check the analysis ID in HulagwAI History. The queue worker and ML service must be running.
- **Inspect logs:** open the extension popup's **Recent scan activity**. For worker diagnostics, open the browser extensions page and inspect the service worker.
