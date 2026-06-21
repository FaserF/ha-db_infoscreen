# -*- coding: utf-8 -*-
import os
import re
import sys
import urllib.request
import json

def get_latest_ha_version():
    try:
        url = "https://pypi.org/pypi/homeassistant/json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data['info']['version']
    except Exception as e:
        print(f"Error fetching HA version: {e}")
        return "2026.6.2"

def clean_and_update_template(file_path, integration_version, ha_version):
    if not os.path.exists(file_path):
        return False
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Update Home Assistant Version placeholder
    # Look for placeholder: 2025.x.x or similar in HA version field description or placeholder
    content = re.sub(
        r"(placeholder:\s*['\"])20\d{2}\.\d{1,2}\.\d{1,2}(['\"])",
        f"\\g<1>{ha_version}\\g<2>",
        content
    )
    
    # 2. Update Integration Version placeholder to the new version
    content = re.sub(
        r"(placeholder:\s*['\"])v?\d+\.\d+\.\d+[^'\"]*(['\"])",
        f"\\g<1>{integration_version}\\g<2>",
        content
    )

    # 3. Privacy/Datenschutz Filter: Check for sensitive fields and strip them or add privacy warning.
    lines = content.splitlines()
    new_lines = []
    skip_mode = False
    skip_indent = 0
    
    for i, line in enumerate(lines):
        # Determine indentation
        indent = len(line) - len(line.lstrip())
        
        if skip_mode:
            if indent > skip_indent:
                continue
            else:
                skip_mode = False
        
        # Check if this line defines a potentially sensitive input field we should remove/modify
        if "- type: input" in line or "- type: textarea" in line:
            field_id = ""
            label_text = ""
            for j in range(1, 10):
                if i + j >= len(lines):
                    break
                next_line = lines[i + j]
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= indent:
                    break
                if "id:" in next_line:
                    field_id = next_line.split("id:")[-1].strip().strip("'\"")
                if "label:" in next_line:
                    label_text = next_line.split("label:")[-1].strip().strip("'\"")
            
            # Identify fields to remove
            sensitive_ids = {"cf_zone", "api_key", "api_token", "token", "password", "phone_number", "phone"}
            sensitive_labels = {"api key", "api token", "password", "token", "private key", "phone number", "phone"}
            
            if field_id.lower() in sensitive_ids or any(sl in label_text.lower() for sl in sensitive_labels):
                print(f"Removing sensitive field: id={field_id}, label={label_text}")
                skip_mode = True
                skip_indent = indent
                continue
        
        if "description:" in line:
            desc_lower = line.lower()
            if any(k in desc_lower for k in ["domain", "host", "ip address", "url", "instance", "address"]):
                if "not share" not in desc_lower and "private" not in desc_lower:
                    line = line.rstrip() + " (Do NOT share sensitive passwords, credentials, or public API keys. Use example.com or 192.168.1.1 instead.)"
                    
        new_lines.append(line)
        
    updated_content = "\n".join(new_lines) + "\n"
    
    if updated_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        return True
    return False

if __name__ == "__main__":
    version = sys.argv[1] if len(sys.argv) > 1 else "v1.0.0"
    if not version.startswith("v") and "." in version:
        version = "v" + version
    
    ha_version = get_latest_ha_version()
    print(f"Updating templates with Integration Version: {version}, HA Version: {ha_version}")
    
    template_dir = ".github/ISSUE_TEMPLATE"
    if os.path.exists(template_dir):
        for filename in os.listdir(template_dir):
            if filename.endswith(".yml") or filename.endswith(".yaml"):
                path = os.path.join(template_dir, filename)
                changed = clean_and_update_template(path, version, ha_version)
                if changed:
                    print(f"Updated: {path}")
