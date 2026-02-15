#!/usr/bin/env python3
"""
snapp_cdp_upload.py - Upload/remove files on SNAPP submission forms via CDP.

Auto-discovers the Chrome page WebSocket URL. Handles hidden file inputs.

Usage:
    python snapp_cdp_upload.py --file <path> --button-text "Upload response"
    python snapp_cdp_upload.py --file <path> --button-text "Upload anonymised manuscript"
    python snapp_cdp_upload.py --file <path> --button-text "Upload figure(s)"
    python snapp_cdp_upload.py --file <path> --button-text "Upload cover letter"
    python snapp_cdp_upload.py --remove <filename_substring>
    python snapp_cdp_upload.py --download <file_url> --output <local_path>

Dependencies: websocket-client (pip install websocket-client)
"""

import argparse
import base64
import json
import sys
import time
import urllib.request
import websocket


def get_page_ws_url():
    """Get the WebSocket URL for the active browser page."""
    data = json.loads(urllib.request.urlopen('http://127.0.0.1:9222/json').read())
    for page in data:
        if page.get('type') == 'page' and 'springernature' in page.get('url', ''):
            return page['webSocketDebuggerUrl']
    # Fallback to first page
    return data[0]['webSocketDebuggerUrl']


def connect():
    """Connect to Chrome via CDP with suppress_origin (mandatory for SNAPP)."""
    ws_url = get_page_ws_url()
    ws = websocket.create_connection(ws_url, suppress_origin=True)
    return ws


_msg_id = 0

def send_cmd(ws, method, params=None):
    """Send a CDP command and wait for the response."""
    global _msg_id
    _msg_id += 1
    cmd = {"id": _msg_id, "method": method}
    if params:
        cmd["params"] = params
    ws.send(json.dumps(cmd))
    while True:
        resp = json.loads(ws.recv())
        if resp.get("id") == _msg_id:
            if "error" in resp:
                print(f"CDP error: {resp['error']}", file=sys.stderr)
            return resp


def upload_file(ws, file_path, button_text):
    """Upload a file to a SNAPP form identified by its button text."""
    send_cmd(ws, "DOM.enable")
    send_cmd(ws, "Runtime.enable")

    # Find the file input within the form that contains the specified button
    js = f"""
        (() => {{
            const forms = document.querySelectorAll('form');
            for (const form of forms) {{
                const btn = form.querySelector('button, input[type="submit"]');
                if (btn && (btn.textContent || btn.value || '').includes('{button_text}')) {{
                    return form.querySelector('input[type="file"]');
                }}
            }}
            return null;
        }})()
    """
    result = send_cmd(ws, "Runtime.evaluate", {
        "expression": js,
        "returnByValue": False
    })

    obj_id = result.get("result", {}).get("result", {}).get("objectId")
    if not obj_id:
        print(f"ERROR: File input not found for button '{button_text}'", file=sys.stderr)
        return False

    # Get the backend node ID
    node_result = send_cmd(ws, "DOM.describeNode", {"objectId": obj_id})
    node_id = node_result["result"]["node"]["backendNodeId"]

    # Set the file
    send_cmd(ws, "DOM.setFileInputFiles", {
        "files": [file_path],
        "backendNodeId": node_id
    })
    time.sleep(1)

    # Click the upload button
    click_js = f"""
        (() => {{
            const forms = document.querySelectorAll('form');
            for (const form of forms) {{
                const btn = form.querySelector('button, input[type="submit"]');
                if (btn && (btn.textContent || btn.value || '').includes('{button_text}')) {{
                    btn.click();
                    return 'clicked';
                }}
            }}
            return 'not found';
        }})()
    """
    send_cmd(ws, "Runtime.evaluate", {"expression": click_js})
    time.sleep(5)
    print(f"Uploaded: {file_path} via '{button_text}'")
    return True


def remove_file(ws, filename_substring):
    """Remove a file from SNAPP using fetch-based form submission."""
    send_cmd(ws, "Runtime.enable")

    js = f"""
        (async () => {{
            const links = document.querySelectorAll('a');
            for (const link of links) {{
                if (link.textContent.includes('{filename_substring}')) {{
                    const container = link.closest('li') || link.parentElement;
                    const form = container ? (container.querySelector('form') || container.closest('form')) : null;
                    if (form) {{
                        const formData = new FormData(form);
                        const resp = await fetch(form.action || window.location.href, {{
                            method: 'POST',
                            body: formData,
                            credentials: 'include'
                        }});
                        return 'Removed: ' + resp.status;
                    }}
                }}
            }}
            return 'Not found';
        }})()
    """
    result = send_cmd(ws, "Runtime.evaluate", {
        "expression": js,
        "awaitPromise": True,
        "returnByValue": True
    })

    value = result.get("result", {}).get("result", {}).get("value", "unknown")
    print(f"Remove '{filename_substring}': {value}")
    return "Removed" in str(value)


def download_file(ws, file_url, output_path):
    """Download a file from SNAPP via XHR in browser context."""
    send_cmd(ws, "Runtime.enable")

    js = f"""
        new Promise((resolve, reject) => {{
            const xhr = new XMLHttpRequest();
            xhr.open('GET', '{file_url}', true);
            xhr.responseType = 'arraybuffer';
            xhr.onload = () => {{
                const bytes = new Uint8Array(xhr.response);
                let binary = '';
                for (let i = 0; i < bytes.byteLength; i++) {{
                    binary += String.fromCharCode(bytes[i]);
                }}
                resolve(btoa(binary));
            }};
            xhr.onerror = () => reject('XHR failed');
            xhr.send();
        }})
    """
    result = send_cmd(ws, "Runtime.evaluate", {
        "expression": js,
        "awaitPromise": True,
        "returnByValue": True
    })

    b64 = result.get("result", {}).get("result", {}).get("value")
    if b64:
        with open(output_path, 'wb') as f:
            f.write(base64.b64decode(b64))
        print(f"Downloaded: {output_path} ({len(b64)} base64 chars)")
        return True
    else:
        print("ERROR: Download failed", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="SNAPP file operations via CDP")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to file to upload")
    group.add_argument("--remove", help="Filename substring to remove")
    group.add_argument("--download", help="File URL to download")

    parser.add_argument("--button-text", help="Upload button text (required for --file)")
    parser.add_argument("--output", help="Output path (required for --download)")
    args = parser.parse_args()

    ws = connect()
    try:
        if args.file:
            if not args.button_text:
                parser.error("--button-text is required for --file")
            success = upload_file(ws, args.file, args.button_text)
        elif args.remove:
            success = remove_file(ws, args.remove)
        elif args.download:
            if not args.output:
                parser.error("--output is required for --download")
            success = download_file(ws, args.download, args.output)
        sys.exit(0 if success else 1)
    finally:
        ws.close()


if __name__ == "__main__":
    main()
