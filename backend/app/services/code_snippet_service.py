"""Generate request code snippets for various languages."""

import json


def generate_code_snippet(api: dict, language: str) -> str:
    """Generate request code snippet for the given API in the specified language."""
    method = api.get("method", "GET")
    path = api.get("path", "/")
    headers = api.get("headers", [])
    params = api.get("params", [])
    body = api.get("body", {"type": "none", "content": ""})

    hdrs = _build_dict(headers)
    qps = _build_dict(params)

    body_content = ""
    body_type = body.get("type", "none") if isinstance(body, dict) else "none"
    if body_type in ("json", "raw", "xml"):
        body_content = body.get("content", "")
    elif body_type in ("form-data", "x-www-form-urlencoded"):
        fields = body.get("fields", [])
        body_content = json.dumps({f.get("key", ""): f.get("value", "") for f in fields if f.get("key")})
    elif body_type == "none":
        body_content = ""

    generators = {
        "curl": _curl,
        "python": _python,
        "javascript": _js,
        "java": _java,
        "go": _go,
        "csharp": _csharp,
    }
    gen = generators.get(language)
    if not gen:
        return f"// Unsupported language: {language}"
    return gen(method, path, hdrs, qps, body_content, body_type)


def _build_dict(items):
    result = {}
    for item in items:
        if isinstance(item, dict) and item.get("key") and item.get("enabled", True) is not False:
            result[item["key"]] = item.get("value", "")
    return result


def _curl(method, path, headers, params, body, body_type):
    parts = [f"curl -X {method} '{path}'"]
    for k, v in headers.items():
        parts.append(f"  -H '{k}: {v}'")
    if body and method in ("POST", "PUT", "PATCH"):
        # 仅在 headers 中未定义 Content-Type 时才追加
        has_ct = any(k.lower() == "content-type" for k in headers)
        if not has_ct:
            ct = "application/json" if body_type == "json" else "application/x-www-form-urlencoded"
            parts.append(f"  -H 'Content-Type: {ct}'")
        escaped = body.replace("'", "'\\''")
        parts.append(f"  -d '{escaped}'")
    return "\n".join(parts)


def _python(method, path, headers, params, body, body_type):
    lines = ["import requests", ""]
    qs = f", params={json.dumps(params)}" if params else ""
    h = json.dumps(headers) if headers else "{}"
    if body and method in ("POST", "PUT", "PATCH"):
        if body_type == "json":
            lines.append(f"response = requests.{method.lower()}('{path}', json={body}{qs}, headers={h})")
        else:
            lines.append(f"response = requests.{method.lower()}('{path}', data=r'''{body}'''{qs}, headers={h})")
    else:
        lines.append(f"response = requests.{method.lower()}('{path}'{qs}, headers={h})")
    lines.append('print("response:", response.status_code, response.text)')
    return "\n".join(lines)


def _js(method, path, headers, params, body, body_type):
    lines = [f"fetch('{path}', {{"]
    lines.append(f"  method: '{method}',")
    if headers:
        indent_h = json.dumps(headers, indent=2).replace("\n", "\n  ")
        lines.append(f"  headers: {indent_h},")
    if body and method in ("POST", "PUT", "PATCH"):
        if body_type == "json":
            lines.append(f"  body: JSON.stringify({body}),")
        else:
            lines.append(f"  body: '{body}',")
    lines.append("})")
    lines.append(".then(res => res.text())")
    lines.append(".then(data => console.log(data));")
    return "\n".join(lines)


def _java(method, path, headers, params, body, body_type):
    lines = ["import java.net.http.*;"]
    lines.append("import java.net.URI;")
    lines.append("")
    lines.append("public class ApiRequest {")
    lines.append("    public static void main(String[] args) throws Exception {")
    lines.append("        var client = HttpClient.newHttpClient();")
    lines.append("        var request = HttpRequest.newBuilder()")
    lines.append(f"            .uri(URI.create(\"{path}\"))")
    for k, v in headers.items():
        lines.append(f'            .header("{k}", "{v}")')
    if body and method in ("POST", "PUT", "PATCH"):
        escaped = body.replace("\\", "\\\\").replace("\"", "\\\"")
        lines.append(f'            .method("{method}", HttpRequest.BodyPublishers.ofString("{escaped}"))')
    else:
        lines.append(f'            .method("{method}", HttpRequest.BodyPublishers.noBody())')
    lines.append("            .build();")
    lines.append("        var response = client.send(request, HttpResponse.BodyHandlers.ofString());")
    lines.append('        System.out.println(response.statusCode() + " " + response.body());')
    lines.append("    }")
    lines.append("}")
    return "\n".join(lines)


def _go(method, path, headers, params, body, body_type):
    lines = ['package main', '', 'import (', '    "fmt"', '    "io"', '    "net/http"', '    "strings"', ')', '', 'func main() {']
    if body and method in ("POST", "PUT", "PATCH"):
        lines.append(f'    payload := strings.NewReader(`{body}`)')
        lines.append(f'    req, _ := http.NewRequest("{method}", "{path}", payload)')
    else:
        lines.append(f'    req, _ := http.NewRequest("{method}", "{path}", nil)')
    for k, v in headers.items():
        lines.append(f'    req.Header.Set("{k}", "{v}")')
    lines.append('    client := &http.Client{}')
    lines.append('    resp, err := client.Do(req)')
    lines.append('    if err != nil { fmt.Println(err); return }')
    lines.append('    defer resp.Body.Close()')
    lines.append('    body, _ := io.ReadAll(resp.Body)')
    lines.append('    fmt.Println(resp.StatusCode, string(body))')
    lines.append('}')
    return "\n".join(lines)


def _csharp(method, path, headers, params, body, body_type):
    lines = ["using System;", "using System.Net.Http;", "using System.Text;", "using System.Threading.Tasks;", ""]
    lines.append("class Program {")
    lines.append("    static async Task Main() {")
    lines.append("        using var client = new HttpClient();")
    for k, v in headers.items():
        lines.append(f'        client.DefaultRequestHeaders.Add("{k}", "{v}");')
    if body and method in ("POST", "PUT", "PATCH"):
        lines.append(f'        var content = new StringContent(@"{body}", Encoding.UTF8, "application/json");')
        lines.append(f'        var response = await client.{method.lower().capitalize()}Async("{path}", content);')
    else:
        lines.append(f'        var response = await client.{method.lower().capitalize()}Async("{path}");')
    lines.append('        Console.WriteLine(response.StatusCode);')
    lines.append('        Console.WriteLine(await response.Content.ReadAsStringAsync());')
    lines.append("    }")
    lines.append("}")
    return "\n".join(lines)
