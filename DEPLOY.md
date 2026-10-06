# Cloudflare Pages 部署指南（GitHub + Pages，.pages.dev 域名）

静态站点已打包好在 `site/` 目录，**23MB、748 个文件**，无需任何构建步骤。

> ✅ **代码已上传完毕**：<https://github.com/Floydzwx/Yuanzhuodongman>
> 仓库结构里有一个叫 `site` 的文件夹，所以 Cloudflare 的**构建输出目录填 `site`**。
> 你只需要做下面「方式一」的第 3、4 步（连 Cloudflare + 填配置）就能上线。

---

## 你需要先准备

1. 一个 **GitHub 账号**（免费就行）
2. 一个 **Cloudflare 账号**（免费套餐够用，Pages 不限量）
3. 本机装了 **Git**（你已经有了）

---

## 方式一：GitHub 网页上传（已完成，别再看这节）

> 这节保留作记录。**代码已经推送到 <https://github.com/Floydzwx/Yuanzhuodongman>，不需要再上传。**
> 当时网页上传失败的原因是：GitHub 网页上传单个目录最多 100 个文件，而 `covers/` 里有 740 张图。
> 用 `git push` 就没有这个限制。

### 第 1 步：建仓库（已完成）

仓库：<https://github.com/Floydzwx/Yuanzhuodongman>

### 第 2 步：上传 site 里的文件（已完成）

已通过 `git push` 上传，740 张封面全部在 `site/covers/` 下。

### 第 3 步：连到 Cloudflare Pages（你需要做的）

1. 登录 <https://dash.cloudflare.com>
2. 左侧边栏点 **Workers 和 Pages**
3. 点 **创建** → 选 **Pages** → 点 **连接到 Git**
4. 授权 GitHub，选择 `Floydzwx/Yuanzhuodongman` 仓库
5. 点 **开始设置**

### 第 4 步：填构建配置（关键，容易填错）

| 配置项 | 填什么 |
|---|---|
| **框架预设** | None |
| **构建命令** | **留空**（不要填任何东西） |
| **构建输出目录** | **`site`** |

> ⚠️ 仓库首页有一个叫 `site` 的文件夹（还有 `cf-worker`、`*.py`），所以输出目录必须填 `site`，不能填 `.`。
> 填错的话页面会 404。

6. 点 **保存并部署**

等 1~3 分钟，部署完成后会给你一个地址，形如：

```
https://yuanshu-anime-archive.pages.dev
```

**这就是你要的 .pages.dev 网址。**

---

## 方式二：命令行上传（已用这个方式完成）

已执行过的命令：

```bash
cd "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"
git remote add origin https://github.com/Floydzwx/Yuanzhuodongman.git
git push -u origin main
```

**以后更新内容**（改完数据后）：

```bash
cd "E:/Artificial Intelligence/WorkBuddy/2026-10-04-13-53-12"

# 1. 重新抓数据（如果你更新了视频列表）
python fetch_full.py

# 2. 重新分类并生成页面
python classify.py
python build_page.py

# 3. 重新压缩封面（只有封面变了才需要）
python prepare_site.py

# 4. 推送
git add -A site/
git commit -m "更新数据"
git push
```

Cloudflare 会自动重新部署（约 1 分钟）。

或者直接双击根目录的 **`文件管理.bat`**，里面第 3 项就是「重新打包并推送」。

---

## 常见问题

**Q：部署后封面不显示？**
- 检查构建输出目录填对没（`site` 还是 `.`）
- 看 `site/index.html` 里封面的引用路径，应该是 `covers/xxx.webp`

**Q：部署失败提示超出限制？**
- 免费版单文件上限 25MB，我们最大的 index.html 才 640KB，不会超
- 如果把 190MB 原始封面也传上去就会出问题 —— 一定要用 `site/` 里的 WebP 版本

**Q：想同时挂上之前的 Cloudflare Worker（自动抓播放量）？**
Pages 和 Worker 可以共存，各自有独立域名。页面里填：
```bash
set WORKER_API=https://你的worker地址
python build_page.py
```
然后重新打包推送。

**Q：页面上的播放量是静态的，怎么更新？**
- 方案A：跑 `export_works.py` + Worker 定时抓（见 `cf-worker/README.md`）
- 方案B：直接重跑 `fetch_full.py` 抓最新播放量再重新打包

---

## 目录说明

```
site/                    ← 部署这个目录（Cloudflare 输出目录填 site）
  index.html             主页面（CSS/JS 全部内联）
  covers/*.webp          740 张封面（190MB → 20MB）
  favicon.ico            标签页图标（圆桌动漫头像）
  up_avatar.jpg          UP 主头像
  me_avatar.jpg          制作者头像
  _headers               缓存策略（封面 1 年强缓存）
  _redirects             跳转配置
  robots.txt

prepare_site.py          把原始封面压成 WebP
package_site.py          生成 site/
make_favicon.py          从头像生成 favicon
文件管理.bat              打包 / 推送 / 删文件的菜单脚本
cf-worker/               自动抓播放量的 Worker（可选）
```

---

## Cloudflare 控制台之外要记住的两件事

**1. 构建输出目录必须是 `site`**，不能是 `.` 或 `root`。
仓库里有 `site/`、`cf-worker/`、`*.py`、`.gitignore`，填 `.` 会把 Python 源码当页面返回。

**2. 不要手动在 GitHub 网页上传 `site/covers/`。**
GitHub 网页上传单个目录上限 100 个文件，740 张图会被拒。要换封面就走 `git push`。
