import base64, binascii, html, json, urllib.parse, re

def multi_decode(value: str):
    original=value
    candidates={"original":value}
    # URL decode
    try: candidates["url"] = urllib.parse.unquote(value)
    except: pass
    # HTML entities
    try: candidates["html"] = html.unescape(value)
    except: pass
    # Base64
    try:
        s=value.strip()
        if len(s)%4==0:
            candidates["base64"]=base64.b64decode(s,validate=True).decode("utf-8",errors="replace")
    except: pass
    # Hex
    try:
        s=re.sub(r"\\x","",value.strip())
        if len(s)%2==0 and re.fullmatch(r"[0-9a-fA-F]+",s):
            candidates["hex"]=bytes.fromhex(s).decode("utf-8",errors="replace")
    except: pass
    # Unicode escape
    try: candidates["unicode"]=value.encode().decode("unicode_escape")
    except: pass
    # ROT13
    import codecs
    try: candidates["rot13"]=codecs.decode(value,"rot_13")
    except: pass
    # JSON
    try: candidates["json"]=json.dumps(json.loads(value),indent=2)
    except: pass
    # Deduplicate
    out=[]
    seen=set()
    for k,v in candidates.items():
        if v not in seen:
            seen.add(v); out.append({"method":k,"result":v})
    return out
