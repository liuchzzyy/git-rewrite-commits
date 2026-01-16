# 指南：使用 git-rewrite-commits 处理其他 GitHub 仓库

本指南将教你如何配置 `git-rewrite-commits` 作为一个“执行器”，自动或手动处理你 GitHub 账号下其他仓库的提交记录。

## 准备工作

在开始之前，你需要准备一个具有目标仓库访问权限的 **Personal Access Token (PAT)**。

### 1. 创建 Personal Access Token (PAT)
1. 访问 GitHub [Tokens 页面](https://github.com/settings/tokens)。
2. 点击 **Generate new token (classic)**。
3. 勾选 **repo** 权限（包含 `repo:status`, `repo_deployment`, `public_repo`, `repo:invite`, `security_events`）。
4. 生成并复制 Token（注意：它只会出现一次）。

### 2. 在当前仓库配置 Secret
1. 进入你当前的 `git-rewrite-commits` 仓库。
2. 点击 **Settings** > **Secrets and variables** > **Actions**。
3. 点击 **New repository secret**。
4. 名称填写：`EXTERNAL_REPO_TOKEN`。
5. 值填写：你刚才复制的 PAT。
6. 同时确保你已经配置了 `DEEPSEEK_API_KEY`（或 OpenAI 相关的 Key）。

---

## 方案一：在当前仓库创建“总控”工作流

你可以创建一个新的工作流文件，专门用来触发对其他库的清理。

在 `.github/workflows/` 目录下创建 `clean-other-repo.yml`:

```yaml
name: Clean External Repository History

on:
  workflow_dispatch:
    inputs:
      target_repo:
        description: '目标仓库 URL (例如: owner/repo)'
        required: true
      max_commits:
        description: '重写最近的提交数量'
        default: '10'
      branch:
        description: '目标分支'
        default: 'master'

jobs:
  rewrite-external:
    runs-on: ubuntu-latest
    steps:
      - name: Install uv
        uses: astral-sh/setup-uv@v5

      - name: Run git-rewrite-commits
        env:
          DEEPSEEK_API_KEY: ${{ secrets.DEEPSEEK_API_KEY }}
        run: |
          # 构建带权限的 URL
          REPO_URL="https://${{ secrets.EXTERNAL_REPO_TOKEN }}@github.com/${{ inputs.target_repo }}.git"
          
          # 执行重写并自动推送
          uv run git-rewrite-commits \
            --provider deepseek \
            --repo "$REPO_URL" \
            --branch "${{ inputs.branch }}" \
            --max-commits ${{ inputs.max_commits }} \
            --push \
            --language zh \
            --skip-remote-consent \
            --quiet
```

---

## 方案二：直接在目标仓库中使用此 Action

如果你希望在目标仓库内运行，只需在目标仓库中创建工作流：

```yaml
name: AI History Cleanup
on:
  workflow_dispatch:

jobs:
  cleanup:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout with Token
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          # 必须使用 PAT 才能在重写后推送回去
          token: ${{ secrets.EXTERNAL_REPO_TOKEN }}

      - name: Rewrite History
        uses: liuchzzyy/git-rewrite-commits@master
        with:
          provider: 'deepseek'
          api_key: ${{ secrets.DEEPSEEK_API_KEY }}
          max_commits: 10
          push: true  # 启用自动推送
          language: 'zh'
```

---

## 核心参数说明

| 参数 | 说明 |
| :--- | :--- |
| `--repo` / `repo:` | 目标仓库地址。支持本地路径或远程 Git URL（需包含 Token）。 |
| `--push` / `push: true` | 重写完成后自动执行 `git push --force`。 |
| `--branch` / `branch:` | 指定要操作的分支。 |
| `--max-commits` | 限制处理的提交数量，防止 API 消耗过快或历史改动过大。 |

## 注意事项

1. **备份**：强制推送历史是不可逆的操作。建议在执行前先手动备份目标仓库。
2. **权限**：如果遇到 `Permission Denied`，请检查 PAT 是否过期或权限是否包含 `repo`。
3. **频率**：建议手动触发（workflow_dispatch），不要使用自动触发，以免造成意外的历史重写。
