

from __future__ import annotations

from html import escape

BRAND_PRIMARY = "#1d4ed8"
BRAND_DARK = "#0f172a"


def money(amount: object, currency: str = "INR") -> str:
    try:
        return f"{currency} {float(amount):,.2f}"
    except (TypeError, ValueError):
        return f"{currency} {amount}"


def layout(
    title: str,
    body_html: str,
    *,
    preheader: str = "",
    footer_text: str = "This is an automated message from the College Library.",
    action_url: str | None = None,
    action_label: str = "Open Library",
) -> str:
    
    button = ""
    if action_url:
        button = f"""
        <tr>
          <td style="padding:8px 32px 28px 32px;">
            <a href="{escape(action_url)}" style="display:inline-block;background:{BRAND_PRIMARY};color:#ffffff;
               text-decoration:none;padding:12px 24px;border-radius:8px;font-weight:600;font-size:15px;">
               {escape(action_label)}
            </a>
          </td>
        </tr>"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{escape(title)}</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:{BRAND_DARK};">
  <span style="display:none;max-height:0;overflow:hidden;opacity:0;">{escape(preheader)}</span>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0"
               style="width:100%;max-width:600px;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 2px 10px rgba(15,23,42,0.08);">
          <tr>
            <td style="background:{BRAND_PRIMARY};padding:22px 32px;">
              <div style="color:#ffffff;font-size:19px;font-weight:700;letter-spacing:0.3px;">College Library</div>
              <div style="color:#dbeafe;font-size:13px;margin-top:2px;">Library Management System</div>
            </td>
          </tr>
          <tr>
            <td style="padding:28px 32px 8px 32px;">
              <h1 style="margin:0 0 14px 0;font-size:21px;line-height:1.3;color:{BRAND_DARK};">{escape(title)}</h1>
              {body_html}
            </td>
          </tr>{button}
          <tr>
            <td style="padding:18px 32px 26px 32px;border-top:1px solid #e2e8f0;color:#64748b;font-size:12px;line-height:1.6;">
              {escape(footer_text)}
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def paragraph(text: str) -> str:
    return f'<p style="margin:0 0 12px 0;font-size:15px;line-height:1.65;">{escape(text)}</p>'


def detail_table(rows: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<tr>'
        f'<td style="padding:9px 0;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px;width:38%;">{escape(k)}</td>'
        f'<td style="padding:9px 0;border-bottom:1px solid #e2e8f0;color:{BRAND_DARK};font-size:14px;font-weight:600;">{escape(v)}</td>'
        f"</tr>"
        for k, v in rows
    )
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:6px 0 18px 0;">{cells}</table>'


def callout(text: str, tone: str = "info") -> str:
    colours = {
        "info": ("#eff6ff", "#1d4ed8"),
        "warning": ("#fffbeb", "#b45309"),
        "danger": ("#fef2f2", "#b91c1c"),
        "success": ("#f0fdf4", "#15803d"),
    }
    bg, fg = colours.get(tone, colours["info"])
    return (
        f'<div style="background:{bg};border-left:4px solid {fg};padding:12px 14px;margin:6px 0 18px 0;'
        f'border-radius:6px;color:{fg};font-size:14px;line-height:1.6;">{escape(text)}</div>'
    )
