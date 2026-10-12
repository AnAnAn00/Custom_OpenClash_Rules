# 用途：每天自动做三件事
#   ① 把上游 Aethersailor/Custom_OpenClash_Rules 的更新合并进你的 fork
#   ② 用 tools/build_my_ini.py 依据上游模板重新生成 cfg/My_Clash.ini
#   ③ 把生成的模板提交回你的仓库
# 放置位置：你 fork 的仓库里新建 .github/workflows/sync-and-build.yml，把下面内容整个粘进去
# 配套文件：tools/build_my_ini.py
name: 自动同步上游并生成我的模板

on:
  schedule:
    - cron: "0 20 * * *"   # 每天 04:00（北京时间 UTC+8）
  workflow_dispatch:       # 想立刻跑一次：Actions 页面 → Run workflow

permissions:
  contents: write          # 允许它把结果写回你的仓库

jobs:
  sync-and-build:
    runs-on: ubuntu-latest
    steps:
      - name: 取出你的仓库
        uses: actions/checkout@v4
        with:
          fetch-depth: 0   # 需要完整历史才能合并上游

      - name: 合并上游最新内容
        run: |
          git remote add upstream https://github.com/Aethersailor/Custom_OpenClash_Rules.git 2>/dev/null || true
          git fetch --no-tags upstream main
          git merge --no-edit FETCH_HEAD

      - name: 生成 cfg/My_Clash.ini
        run: python3 tools/build_my_ini.py

      - name: 提交并推送
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add cfg/My_Clash.ini
          if git diff --cached --quiet; then
            echo "模板没有变化，跳过提交"
          else
            git commit -m "chore: 自动生成 cfg/My_Clash.ini"
            git push origin HEAD
          fi
