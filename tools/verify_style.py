#!/usr/bin/env python3
"""verify_style.py — Style 包验证门（fail-closed）
用法: python3 tools/verify_style.py styles/001-youyin [--stage identity|full]
  identity: style.json + SPIRIT.md + prompt-face.md + provenance/ 齐备且 token 合规
  full:     identity + article-face.css + specimen.html + examples/
检查: 文件齐备 / token 双主题角色齐备 / hex 合法 / WCAG 对比度 / 禁纯黑 / 红标点落位规则
输出: [VERIFY] key=value 行 + 末行 STYLE_GATE=PASS|FAIL（FAIL 时 exit 1）
"""
import os, sys, json, re

REQ_ROLES = ["surface-1", "surface-2", "surface-inverse", "text-primary",
             "text-secondary", "text-inverse", "text-on-ink",
             "accent-1", "accent-2"]
IDENTITY_FILES = ["style.json", "SPIRIT.md", "prompt-face.md",
                  "provenance/notes.md"]
# 公开层禁词（裁决 B, 2026-07-26）——拼接写法防自拦
FORBIDDEN_TEXT = ["私有" "风格矩阵", "private" "-style-matrix", "auto" "journey"]
FULL_FILES = IDENTITY_FILES + ["article-face.css", "specimen.html"]

def luminance(hexc):
    r, g, b = (int(hexc[i:i+2], 16) / 255 for i in (1, 3, 5))
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)

def contrast(a, b):
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)

def main():
    style_dir = sys.argv[1]
    stage = "identity"
    if "--stage" in sys.argv:
        stage = sys.argv[sys.argv.index("--stage") + 1]
    files = FULL_FILES if stage == "full" else IDENTITY_FILES
    failures = []

    for f in files:
        p = os.path.join(style_dir, f)
        ok = os.path.exists(p) and os.path.getsize(p) > 0
        print(f"[VERIFY] file:{f}={'OK' if ok else 'MISSING'}")
        if not ok:
            failures.append(f"missing:{f}")

    sj_path = os.path.join(style_dir, "style.json")
    if os.path.exists(sj_path):
        sj = json.load(open(sj_path))
        for key in ["id", "name", "provenance", "essence", "tokens",
                    "typography", "composition", "prompt_fragment", "anti"]:
            ok = key in sj and sj[key]
            print(f"[VERIFY] schema:{key}={'OK' if ok else 'MISSING'}")
            if not ok:
                failures.append(f"schema:{key}")
        tex = sj.get("texture", {})
        for sub in ["image", "web"]:
            ok = isinstance(tex.get(sub), dict) and tex[sub]
            print(f"[VERIFY] texture-split:{sub}={'OK' if ok else 'MISSING'}")
            if not ok:
                failures.append(f"texture-split:{sub}")
        css_path = os.path.join(style_dir, "article-face.css")
        if os.path.exists(css_path):
            css = open(css_path).read().lower()
            for theme in ["light", "dark"]:
                for role in REQ_ROLES:
                    v = sj.get("tokens", {}).get(theme, {}).get(role, {}).get("value", "")
                    ok = bool(v) and v.lower() in css
                    print(f"[VERIFY] css-token:{theme}:{role}={'OK' if ok else 'ABSENT'}")
                    if not ok:
                        failures.append(f"css-token:{theme}:{role}")
        for theme in ["light", "dark"]:
            toks = sj.get("tokens", {}).get(theme, {})
            vals = {}
            for role in REQ_ROLES:
                v = toks.get(role, {}).get("value", "")
                good = bool(re.fullmatch(r"#[0-9A-Fa-f]{6}", v))
                vals[role] = v if good else None
                print(f"[VERIFY] token:{theme}:{role}={v if good else 'BAD'}")
                if not good:
                    failures.append(f"token:{theme}:{role}")
            if all(vals.get(r) for r in ["surface-1", "text-primary",
                                          "text-secondary", "surface-2",
                                          "surface-inverse", "text-on-ink",
                                          "text-inverse", "accent-2"]):
                checks = [
                    (f"contrast:{theme}:text-primary/surface-1",
                     contrast(vals["text-primary"], vals["surface-1"]), 4.5),
                    (f"contrast:{theme}:text-secondary/surface-1",
                     contrast(vals["text-secondary"], vals["surface-1"]), 4.5),
                    # 反相对必须成对出现: text-inverse 的法定落点是 surface-inverse
                    (f"contrast:{theme}:text-inverse/surface-inverse",
                     contrast(vals["text-inverse"], vals["surface-inverse"]), 4.5),
                    # 墨场上的字恒为 text-on-ink（组件级配对，防"墨字落墨场"复发）
                    (f"contrast:{theme}:text-on-ink/surface-2",
                     contrast(vals["text-on-ink"], vals["surface-2"]), 4.5),
                ]
                # accent-2 的落点由风格自行申报（rules.accent2_pairing，默认 surface-1）
                # 例: 油印"红只落墨场"→surface-2；水粉/孔雀"红可落纸"→surface-1
                pairing = sj.get("rules", {}).get("accent2_pairing", "surface-1")
                if vals.get(pairing):
                    checks += [
                        (f"contrast:{theme}:accent-2/{pairing}",
                         contrast(vals["accent-2"], vals[pairing]), 3.0),
                ]
                for name, ratio, need in checks:
                    ok = ratio >= need
                    print(f"[VERIFY] {name}={ratio:.2f} (need>={need})"
                          f"{'' if ok else ' FAIL'}")
                    if not ok:
                        failures.append(name)
                for role, v in vals.items():
                    if v and v.upper() == "#000000":
                        print(f"[VERIFY] pure-black-ban:{theme}:{role}=FAIL")
                        failures.append(f"pureblack:{theme}:{role}")

    # 泄露扫描: 公开文件不得含 9 位以上连续数字（风格码量级；脱敏立法 2026-07-25）
    for root, _, fs in os.walk(style_dir):
        for f in fs:
            if f.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                continue
            txt = open(os.path.join(root, f), errors="ignore").read()
            hits = re.findall(r"\d{9,}", txt)
            hits += [w for w in FORBIDDEN_TEXT if w.lower() in txt.lower()]
            if hits:
                print(f"[VERIFY] leak:{f}={hits[:3]}")
                failures.append(f"leak:{f}")

    print(f"[VERIFY] stage={stage} failures={len(failures)}")
    if failures:
        print("STYLE_GATE=FAIL")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print("STYLE_GATE=PASS")

if __name__ == "__main__":
    main()
