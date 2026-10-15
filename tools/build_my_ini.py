#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从上游模板自动生成你自己的精简模板。

输入（上游那份，永远不要手改）: cfg/Custom_Clash_Full_Fallback.ini
输入（上游那份，永远不要手改）: cfg/Custom_Clash_Full.ini
输出（你的那份，订阅里 config= 指向它）: cfg/My_Clash.ini

用法:
    python3 tools/build_my_ini.py
    python3 tools/build_my_ini.py 源文件 输出文件

上游每次更新后重跑一遍即可；GitHub Actions 里也是跑这个脚本。
要调整规则，只改下面 CONFIG 区的常量。
"""
import pathlib
import sys

# Windows 控制台默认 GBK，打印 emoji 会报错；统一成 UTF-8
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ==================== CONFIG ====================
SRC_DEFAULT = "cfg/Custom_Clash_Full_Fallback.ini"
SRC_DEFAULT = "cfg/Custom_Clash_Full.ini"
DST_DEFAULT = "cfg/My_Clash.ini"

AUTO = "♻️ 自动选择"

# ==================== 模式 ====================
# True（默认）= 极简模式，只做三件事，其它一律保持上游原样：
#   ① 删掉「🚀 手动选择」分组，凡是引用它的成员都改成「♻️ 自动选择」
#   ② 删掉「🌐 其他地区」分组及其引用
#   ③ 「♻️ 自动选择」保持 url-test + .*（也就是全部 CF优选 节点）
# False = 之前那套完整优化（删空地区分组、DNS 规则、Steam/游戏平台默认走代理……）
MINIMAL_MODE = True

# 极简模式专用：整组删掉。值不是 None 时，引用它的地方会改成该分组
MINIMAL_DELETE = {
    "🚀 手动选择": AUTO,
    "🌐 其他地区": None,
    # 你的节点池里没有这些地区/属性名，这些组匹配不到任何节点（等于空组）→ 整组删掉
    "🇭🇰 香港节点": None,
    "🇺🇸 美国节点": None,
    "🇯🇵 日本节点": None,
    "🇸🇬 新加坡节点": None,
    "🇼🇸 台湾节点": None,
    "🇰🇷 韩国节点": None,
    "🇨🇦 加拿大节点": None,
    "🇬🇧 英国节点": None,
    "🇫🇷 法国节点": None,
    "🇩🇪 德国节点": None,
    "🇳🇱 荷兰节点": None,
    "🇹🇷 土耳其节点": None,
    "🇷🇺 俄罗斯节点": None,
    "🏠 家宽节点": None,
    "🐢 低倍率节点": None,
}

# 除了这些分组，其它分组的默认（成员第一位）都改成「♻️ 自动选择」＝走代理
DIRECT_ONLY_GROUPS = {"🎯 全球直连"}
PROXY_FIRST_ALL = True
# ================================================

# 你的节点里没有这些地区/关键字，或者和「自动选择」完全重复 → 整组删掉
REMOVE_GROUPS = {
    "🇭🇰 香港节点", "🇺🇸 美国节点", "🇯🇵 日本节点", "🇸🇬 新加坡节点",
    "🇼🇸 台湾节点", "🇰🇷 韩国节点", "🇨🇦 加拿大节点", "🇬🇧 英国节点",
    "🇫🇷 法国节点", "🇩🇪 德国节点", "🇳🇱 荷兰节点", "🇹🇷 土耳其节点",
    "🇷🇺 俄罗斯节点", "🏠 家宽节点", "🐢 低倍率节点", "🌐 其他地区",
}

# 「自动选择」组的行为：
#   "url-test" = 自动在全部节点里挑一个能用的（推荐：CF 优选 IP 会不断有挂掉的）
#   "select"   = 固定用你手点的那个节点；注意：如果那个节点挂了，
#                所有把它当成员的 fallback 分组（GitHub/ChatGPT 等）会自动跳到「全球直连」
AUTO_MODE = "url-test"
AUTO_TOLERANCE = "500"
TEST_URL = "http://www.gstatic.com/generate_204"

DIRECT_GROUP = "🎯 全球直连"

# 「🎯 全球直连」这个分组要不要也走代理：
#   "proxy"  = 默认走代理（成员：♻️ 自动选择 > DIRECT，面板里可以一键切回直连）
#   "direct" = 保持上游原样（纯直连）—— 默认用这个
GLOBAL_DIRECT_MODE = "direct"

# 想让某几条「全球直连」的规则也走代理，就写在这里（左边是规则集关键字，右边是目标分组）
# 例子：把 Steam 下载 CDN 和游戏平台下载也走代理
#   REPOINT_RULES = {
#       "Steam_CDN_Classical.yaml": "🎮 Steam",
#       "category-game-platforms-download": "🎮 Steam",
#   }
REPOINT_RULES = {}

# 插到规则最前面的自定义规则（左边 = 目标分组，右边 = Clash 规则串）
# 目的：DNS 相关的流量别再被末尾那条 `DstPort 1-79 → 🔀 非标端口` 抓走。
#   - 明文 DNS（53）永远直连，不再依赖「非标端口」组当前选中的节点；
#   - 国外 DoH 用的几个 IP 钉死走代理（配合把 fallback 换成 DoH 使用），
#     这样即使「非标端口」是直连，国外解析也不会被污染或阻断。
PREPEND_RULES = [
    ("🎯 全球直连", "[]DST-PORT,53"),
    ("♻️ 自动选择", "[]IP-CIDR,8.8.8.8/32,no-resolve"),
    ("♻️ 自动选择", "[]IP-CIDR,8.8.4.4/32,no-resolve"),
    ("♻️ 自动选择", "[]IP-CIDR,1.1.1.1/32,no-resolve"),
    ("♻️ 自动选择", "[]IP-CIDR,1.0.0.1/32,no-resolve"),
]

# Steam CM（登录）域名默认按上游设计走直连。
# 如果 DNS 修好后登录依然不稳，把它改成 True，就会在最前面插一条走代理的规则。
STEAM_CM_PROXY = False

# 即使「全球直连」走代理，下面这些规则集也强制保持直连。
# 内网/局域网规则走代理会导致路由器、NAS、投屏、Tailscale 之类的功能直接失效，
# 下载 CDN、游玩平台、公开 Tracker 走代理也会变慢或失败。
KEEP_DIRECT_PATTERNS = (
    "GEOSITE,private",
    "GEOIP,private",
    "Custom_Direct_Domain.mrs",
    "Custom_Direct_Classical_IP.yaml",
    "Steam_CDN_Classical.yaml",
    "category-games@cn",
    "category-game-platforms-download",
    "category-public-tracker",
    "GEOSITE,google-cn",
)

# 这些分组里把「自动选择」提到第一位（= 默认就走代理）
# 其余分组保持上游顺序，比如「苹果服务/微软服务/国内AI服务」默认仍是直连
AUTO_FIRST_GROUPS = {
    "🌍 国外域名",
    "🎮 Steam",      # Steam 商店/社区/登录默认走代理，否则直连会登录不上
    "🎮 游戏平台",   # 国内游戏域名(category-games@cn)在更前面，仍然直连
}

# 这些组的成员列表强制重写，避免指向被删掉的分组（否则会走直连）
FORCE_MEMBERS = {
    "🐟 漏网之鱼": [AUTO, "DIRECT"],
    # 非标端口（PT/BT 等）默认直连，需要时可在面板里切到「漏网之鱼」走代理
    "🔀 非标端口": ["🎯 全球直连", "🐟 漏网之鱼"],
    # 非标端口（PT/BT 等）默认直连，需要时可在面板里切到「漏网之鱼」走代理。
    # 这里直接写 DIRECT，避免「全球直连」改成代理后把它带跑。
    "🔀 非标端口": ["DIRECT", "🐟 漏网之鱼"],
}

# Full 版里的「手动选择」类分组：改成「先自动选择，再列出所有节点」。
# 这样默认用的是活着的节点（自动选择），想固定时又能从列表里挑具体节点。
MANUAL_GROUPS = {
    "🚀 手动选择": ["select", f"[]{AUTO}", ".*"],
    "🚀 手动切换": ["select", f"[]{AUTO}", ".*"],
}
if GLOBAL_DIRECT_MODE == "proxy":
    # 默认走代理，但保留 DIRECT 作为可切换项
    FORCE_MEMBERS[DIRECT_GROUP] = [AUTO, "DIRECT"]
# ================================================


def parse_fields(line: str, prefix: str):
    """把 custom_proxy_group=组名`类型`... 拆成字段列表"""
    return line[len(prefix):].split("`")


def transform_minimal(lines):
    """极简模式：只删分组、改引用，其它原样不动"""
    out, dropped, renamed, dropped_refs, rules_fixed = [], set(), 0, 0, []
    for line in lines:
        s = line.strip()

        if s.startswith("custom_proxy_group="):
            fields = parse_fields(line, "custom_proxy_group=")
            if fields[0].strip() in MINIMAL_DELETE:
                dropped.add(fields[0].strip())
                continue
            name = fields[0].strip()
            members, params = [], []
            for f in fields[2:]:
                if f.startswith("[]"):
                    target = f[2:].strip()
                    if target in MINIMAL_DELETE:
                        new = MINIMAL_DELETE[target]
                        if new is None:
                            dropped_refs += 1
                            continue
                        target = new
                        renamed += 1
                    if target not in members:   # 改名后可能重复，去重
                        members.append(target)
                else:
                    params.append(f)

            # 除了「🎯 全球直连」，其它分组的默认值都设为「♻️ 自动选择」（走代理）
            if PROXY_FIRST_ALL and name not in DIRECT_ONLY_GROUPS and name != AUTO:
                if AUTO in members:
                    members.remove(AUTO)
                members.insert(0, AUTO)

            out.append(
                "custom_proxy_group="
                + "`".join([fields[0], fields[1]] + [f"[]{m}" for m in members] + params)
            )
            continue

        if s.startswith("ruleset=") or s.startswith("clash_rule="):
            prefix = "ruleset=" if s.startswith("ruleset=") else "clash_rule="
            body = line[len(prefix):]
            if "," in body:
                target, rest = body.split(",", 1)
                if target.strip() in MINIMAL_DELETE:
                    new = MINIMAL_DELETE[target.strip()] or "DIRECT"
                    rules_fixed.append(f"{rest.strip()[:60]} → {new}")
                    line = f"{prefix}{new},{rest}"
            out.append(line)
            continue

        out.append(line)
    return out, dropped, renamed, dropped_refs, rules_fixed


def rebuild_auto(fields):
    """重写「自动选择」组的类型和参数"""
    regex = fields[2] if len(fields) > 2 else ".*"
    if AUTO_MODE == "select":
        # select 组不需要测速参数，只保留 名称/类型/正则
        return [fields[0], "select", regex]
    url = fields[3] if len(fields) > 3 and fields[3].startswith("http") else TEST_URL
    return [fields[0], "url-test", regex, url, f"300,{AUTO_TOLERANCE},50"]


def build(src: pathlib.Path, dst: pathlib.Path) -> int:
    if not src.exists():
        print(f"[错误] 找不到源文件 {src}")
        print("       上游是不是把模板改名了？去 cfg/ 目录看一眼，然后改脚本里的 SRC_DEFAULT")
        return 1

    lines = src.read_text(encoding="utf-8").splitlines()

    if MINIMAL_MODE:
        out_lines, dropped, renamed, dropped_refs, rules_fixed = transform_minimal(lines)
        dst.parent.mkdir(parents=True, exist_ok=True)
        with open(dst, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(out_lines) + "\n")
        print(f"[完成] 生成 {dst}（{len(out_lines)} 行，极简模式）")
        print(f"  删除分组 {len(dropped)} 个: {', '.join(sorted(dropped)) or '无'}")
        print(f"  成员引用改为 {AUTO}: {renamed} 处")
        print(f"  成员引用删除: {dropped_refs} 处")
        if rules_fixed:
            print(f"  规则改指向: {', '.join(rules_fixed)}")
        return 0

    prepend = list(PREPEND_RULES)
    if STEAM_CM_PROXY:
        prepend.insert(0, ("🎮 Steam", "[]DOMAIN-SUFFIX,steamserver.net"))
    prepend_lines = [f"ruleset={group},{rule}" for group, rule in prepend]
    insert_at = next(
        (i for i, l in enumerate(lines) if l.strip().startswith(("ruleset=", "clash_rule="))),
        len(lines),
    )

    out_lines = []
    removed, fixed, repointed = set(), [], []
    removed, fixed, repointed, kept_direct, manual = set(), [], [], [], []
    auto_found = False

    for line in lines:
    for idx, line in enumerate(lines):
        if idx == insert_at:
            out_lines.extend(prepend_lines)
        stripped = line.strip()

        if stripped.startswith("custom_proxy_group="):
            fields = parse_fields(line, "custom_proxy_group=")
            name = fields[0].strip()

            if name in REMOVE_GROUPS:
                removed.add(name)
                continue

            if name in MANUAL_GROUPS:
                out_lines.append("custom_proxy_group=" + "`".join([fields[0]] + MANUAL_GROUPS[name]))
                manual.append(name)
                continue

            if name == AUTO:
                auto_found = True
                fields = rebuild_auto(fields)
                out_lines.append("custom_proxy_group=" + "`".join(fields))
                continue

            if name in FORCE_MEMBERS:
                # 成员换成新的，但行尾的测速参数（url/间隔）必须原样保留，
                # 否则 fallback/url-test 分组会因为缺测速地址被丢弃
                params = [f for f in fields[2:] if not f.startswith("[]")]
                fields = [fields[0], fields[1]] + [f"[]{m}" for m in FORCE_MEMBERS[name]] + params
                fixed.append(name)
                out_lines.append("custom_proxy_group=" + "`".join(fields))
                continue

            # 普通分组：删掉对被移除分组的引用
            gtype = fields[1] if len(fields) > 1 else "select"
            members, params, lost_proxy = [], [], False
            for f in fields[2:]:
                if f.startswith("[]"):
                    target = f[2:].strip()
                    if target in REMOVE_GROUPS:
                        if target not in ("DIRECT", "REJECT"):
                            lost_proxy = True
                        continue
                    if target and target not in members:
                        members.append(target)
                else:
                    params.append(f)

            if lost_proxy and AUTO not in members:
                # 原来靠地区分组走代理，现在这些组没了 → 改成走「自动选择」，别退化成直连
                members.insert(0, AUTO)
                fixed.append(name)
            if name in AUTO_FIRST_GROUPS and AUTO in members:
                members.remove(AUTO)
                members.insert(0, AUTO)
            if not members and not params:
                # 成员被删光、也没有正则可用 → 兜底
                members = [AUTO, "DIRECT"] if gtype in ("select", "fallback") else [AUTO]

            new_fields = [fields[0], gtype] + [f"[]{m}" for m in members] + params
            out_lines.append("custom_proxy_group=" + "`".join(new_fields))
            continue

        # 规则行如果指向被删掉的分组，改成指向「自动选择」，避免规则失效
        for prefix in ("ruleset=", "clash_rule="):
            if stripped.startswith(prefix):
                body = line[len(prefix):]
                if "," in body:
                    target, rest = body.split(",", 1)
                    if target.strip() in REMOVE_GROUPS:
                        repointed.append(target.strip())
                        line = f"{prefix}{AUTO},{rest}"
                    elif (
                        GLOBAL_DIRECT_MODE == "proxy"
                        and target.strip() == DIRECT_GROUP
                        and any(p in rest for p in KEEP_DIRECT_PATTERNS)
                    ):
                        kept_direct.append(rest.split(",")[0].strip() or rest[:40])
                        line = f"{prefix}DIRECT,{rest}"
                    else:
                        for pattern, group in REPOINT_RULES.items():
                            if target.strip() == DIRECT_GROUP and pattern in rest:
                                repointed.append(f"{rest.split(',')[0].strip()[:48]} → {group}")
                                line = f"{prefix}{group},{rest}"
                                break
                break
        out_lines.append(line)

    dst.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" 保证 Windows 本地和 GitHub Actions 生成的文件字节一致
    with open(dst, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(out_lines) + "\n")

    print(f"[完成] 生成 {dst}（{len(out_lines)} 行）")
    print(f"  删除分组 {len(removed)} 个: {', '.join(sorted(removed)) or '无'}")
    if manual:
        print(f"  手动分组改写: {', '.join(manual)}")
    print(f"  成员补全/重写: {', '.join(fixed) or '无'}")
    print(f"  规则改指向 {AUTO}: {', '.join(sorted(set(repointed))) or '无'}")
    if GLOBAL_DIRECT_MODE == "proxy":
        print(f"  「{DIRECT_GROUP}」改为走代理；{len(kept_direct)} 条规则集强制保持直连")
    print(f"  规则最前面插入自定义规则 {len(prepend_lines)} 条（DNS 相关）")

    missing = REMOVE_GROUPS - removed
    if missing:
        print(f"  [提醒] 模板里没找到这些分组（可能上游改名了）: {', '.join(sorted(missing))}")
    if not auto_found:
        print(f"  [提醒] 没找到「{AUTO}」分组，检查一下上游模板")
    return 0


BUILTIN_TARGETS = {"DIRECT", "REJECT", "PASS", "COMPATIBLE", "GLOBAL"}


def self_check(path: pathlib.Path) -> bool:
    """生成后自检：分组名唯一、引用都能解析、自动分组带测速地址"""
    lines = path.read_text(encoding="utf-8").splitlines()
    groups, refs, rule_targets, no_url = [], [], [], []

    for line in lines:
        s = line.strip()
        if s.startswith("custom_proxy_group="):
            fields = line[len("custom_proxy_group="):].split("`")
            groups.append(fields[0].strip())
            for f in fields[2:]:
                if f.startswith("[]"):
                    refs.append(f[2:].strip())
            if len(fields) > 1 and fields[1] in ("fallback", "url-test"):
                if not any(f.startswith("http") for f in fields[2:]):
                    no_url.append(fields[0].strip())
        elif s.startswith("ruleset="):
            body = line[line.index("ruleset=") + 8:]
            if "," in body:
                rule_targets.append(body.split(",", 1)[0].strip())

    seen, dup = set(), set()
    for g in groups:
        if g in seen:
            dup.add(g)
        seen.add(g)
    gset = set(groups)
    bad_refs = sorted({r for r in refs if r and r not in gset and r not in BUILTIN_TARGETS})
    bad_rules = sorted({t for t in rule_targets if t and t not in gset and t not in BUILTIN_TARGETS})

    print(f"[自检] {path}")
    print(f"  分组 {len(groups)} 个 / 规则 {len(rule_targets)} 条 / 成员引用 {len(refs)} 个")
    ok = True
    for label, bad in (
        ("分组重名", sorted(dup)),
        ("悬空引用", bad_refs),
        ("规则指向不存在的分组", bad_rules),
        ("缺测速地址的自动分组", no_url),
    ):
        print(f"  {label}: {', '.join(bad) if bad else '无'}")
        if bad:
            ok = False
    return ok


def main():
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else SRC_DEFAULT)
    dst = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else DST_DEFAULT)
    sys.exit(build(src, dst))
    code = build(src, dst)
    if code:
        sys.exit(code)
    # 生成后自检：宁可这里报错，也别让 OpenClash 加载时报"引用不存在的分组"
    if not self_check(dst):
        print("[错误] 自检不通过，这份 ini 先别用")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
