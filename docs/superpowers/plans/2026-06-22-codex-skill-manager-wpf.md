# Codex Skill Manager WPF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished, single-file self-contained WPF desktop app for managing Codex skills, with bilingual skill details, source links, refresh/update actions, and a desktop shortcut.

**Architecture:** A new WPF app will own the UI, while a small service layer reads skill folders from `C:\Users\ZS\.codex\skills` and `C:\Users\ZS\.codex\skills-disabled`, extracts metadata from each `SKILL.md`, and executes enable/disable/move/update operations through the existing PowerShell toggle workflow. The app will surface a modern dark interface with grouped skill lists, a right-side details panel, and explicit refresh/update commands so the user can inspect and manage skills without opening PowerShell. Publishing will target a self-contained single-file Windows build and a desktop shortcut for one-click launch.

**Tech Stack:** .NET 6 WPF, C#, PowerShell interop for skill moves and updates, Windows packaging/publish profile.

## Global Constraints

- Default state remains: `brainstorming` stays enabled and all other skills stay disabled unless explicitly turned on.
- Active skills live in `C:\Users\ZS\.codex\skills`; disabled skills live in `C:\Users\ZS\.codex\skills-disabled`.
- The app must run on Windows and be published as a self-contained single-file executable.
- Skill details must show both Chinese and English text for function and usage.
- Skill details must include the original source link when available, and a last-updated/status area.
- The UI should use a deliberate polished dark visual style, not the default WPF chrome.
- The app must expose separate `Refresh` and `Update` actions.

---

### Task 1: Create the WPF project skeleton

**Files:**
- Create: `E:\notebook\codex-skill-manager-wpf\CodexSkillManager.csproj`
- Create: `E:\notebook\codex-skill-manager-wpf\App.xaml`
- Create: `E:\notebook\codex-skill-manager-wpf\App.xaml.cs`
- Create: `E:\notebook\codex-skill-manager-wpf\MainWindow.xaml`
- Create: `E:\notebook\codex-skill-manager-wpf\MainWindow.xaml.cs`
- Create: `E:\notebook\codex-skill-manager-wpf\README.md`

**Interfaces:**
- Produces: a buildable WPF shell with a main window, app entrypoint, and a project file that targets Windows desktop.
- Consumes: .NET 6 WindowsDesktop runtime already installed on the machine.

- [ ] **Step 1: Write the failing build check**

```powershell
cd E:\notebook\codex-skill-manager-wpf
if (Test-Path .\CodexSkillManager.csproj) { 'project-exists' } else { 'missing-project' }
```

Expected: `missing-project`

- [ ] **Step 2: Add the minimal WPF project files**

Create a `.csproj` that targets `net6.0-windows`, sets `<UseWPF>true</UseWPF>`, and prepares the app for later single-file publish.

- [ ] **Step 3: Run a sanity build**

Run: `dotnet build E:\notebook\codex-skill-manager-wpf\CodexSkillManager.csproj`
Expected: Build succeeds or fails only because the UI/body is still minimal.

- [ ] **Step 4: Commit the skeleton**

```powershell
git -C E:\notebook add codex-skill-manager-wpf
git -C E:\notebook commit -m "feat: scaffold WPF skill manager"
```

### Task 2: Implement skill metadata loading and bilingual detail extraction

**Files:**
- Create: `E:\notebook\codex-skill-manager-wpf\Models\SkillItem.cs`
- Create: `E:\notebook\codex-skill-manager-wpf\Services\SkillCatalogService.cs`
- Create: `E:\notebook\codex-skill-manager-wpf\Services\SkillMetadataParser.cs`
- Create: `E:\notebook\codex-skill-manager-wpf\Services\SkillSourceIndex.cs`

**Interfaces:**
- Consumes: the project skeleton from Task 1.
- Produces: `SkillItem` records with `Name`, `Status`, `FolderPath`, `SkillFilePath`, `ChineseFunction`, `EnglishFunction`, `ChineseUsage`, `EnglishUsage`, `SourceUrl`, and `LastUpdatedText`.

- [ ] **Step 1: Write a parser test harness inside a console-style temp check**

```powershell
cd E:\notebook\codex-skill-manager-wpf
# The parser should later be able to read a SKILL.md and extract name, description, and source link.
```

Expected: no implementation yet, but the task defines the data we will verify.

- [ ] **Step 2: Implement metadata parsing**

Read `SKILL.md` frontmatter and body text, preserve existing Chinese/English content, and extract a best-effort source URL from fields like `homepage`, `source`, or markdown links when present.

- [ ] **Step 3: Implement source index lookup**

Create a small source map file in the app project that can remember known source URLs for skills that do not expose a link in frontmatter. Use this as the fallback for the `原链接 / Source` panel and update flow.

- [ ] **Step 4: Verify the catalog output**

Run the app or a small helper to print one parsed skill and confirm it includes both Chinese and English text plus a source URL when available.

- [ ] **Step 5: Commit the metadata layer**

```powershell
git -C E:\notebook add codex-skill-manager-wpf\Models codex-skill-manager-wpf\Services
git -C E:\notebook commit -m "feat: parse skill metadata"
```

### Task 3: Build the polished WPF interface

**Files:**
- Modify: `E:\notebook\codex-skill-manager-wpf\MainWindow.xaml`
- Modify: `E:\notebook\codex-skill-manager-wpf\MainWindow.xaml.cs`
- Create: `E:\notebook\codex-skill-manager-wpf\Theme\Colors.cs`
- Create: `E:\notebook\codex-skill-manager-wpf\Theme\Styles.xaml`

**Interfaces:**
- Consumes: `SkillItem` from Task 2.
- Produces: a dark, card-based UI with grouped lists, search, a right-side detail pane, and selection-driven updates.

- [ ] **Step 1: Write the window layout**

Use a three-zone WPF layout: left skill list, center action column, right detail pane. Style the window with a non-default dark palette, rounded cards, stronger spacing, and custom accent chips.

- [ ] **Step 2: Bind selection to detail content**

When a skill is selected, show `功能 / Function`, `用法 / Usage`, `原链接 / Source`, and `更新说明 / Update Notes` with Chinese and English text side by side or stacked.

- [ ] **Step 3: Add search and status chips**

Include a search box that filters skills live and badges for `默认关闭`, `brainstorming`, and total enabled/disabled counts.

- [ ] **Step 4: Run the UI and inspect it visually**

Launch the app and check that the layout looks intentionally designed rather than like a default WPF prototype.

- [ ] **Step 5: Commit the interface**

```powershell
git -C E:\notebook add codex-skill-manager-wpf\MainWindow.xaml codex-skill-manager-wpf\MainWindow.xaml.cs codex-skill-manager-wpf\Theme
git -C E:\notebook commit -m "feat: polish skill manager ui"
```

### Task 4: Add enable, disable, refresh, and update commands

**Files:**
- Create: `E:\notebook\codex-skill-manager-wpf\Services\SkillToggleService.cs`
- Create: `E:\notebook\codex-skill-manager-wpf\Services\SkillUpdateService.cs`
- Modify: `E:\notebook\codex-skill-manager-wpf\MainWindow.xaml.cs`
- Create: `E:\notebook\codex-skill-manager-wpf\Commands\RefreshCommand.cs`
- Create: `E:\notebook\codex-skill-manager-wpf\Commands\UpdateCommand.cs`

**Interfaces:**
- Consumes: the parsed skill catalog and the existing folder-based enable/disable model.
- Produces: button handlers for `Enable`, `Disable`, `Refresh`, and `Update`.

- [ ] **Step 1: Write command behaviors first**

`Refresh` rereads local folders and rebuilds the UI. `Update` re-fetches or re-imports the skill source content, then refreshes the local catalog.

- [ ] **Step 2: Implement the folder toggle path**

Reuse the current move-based enable/disable strategy: move skill folders between `C:\Users\ZS\.codex\skills` and `C:\Users\ZS\.codex\skills-disabled`.

- [ ] **Step 3: Implement update flow**

For skills with a known source URL, re-download or re-install from that source, then refresh metadata. For skills without a source URL, surface a clear message that update is unavailable until a source is registered.

- [ ] **Step 4: Wire up button handlers and messages**

Connect the buttons to the service layer and show success/failure feedback in the window.

- [ ] **Step 5: Commit the actions layer**

```powershell
git -C E:\notebook add codex-skill-manager-wpf\Services\SkillToggleService.cs codex-skill-manager-wpf\Services\SkillUpdateService.cs codex-skill-manager-wpf\Commands codex-skill-manager-wpf\MainWindow.xaml.cs
git -C E:\notebook commit -m "feat: add skill actions"
```

### Task 5: Publish self-contained single-file EXE and create the desktop shortcut

**Files:**
- Create: `E:\notebook\codex-skill-manager-wpf\Properties\PublishProfiles\win-x64-self-contained.pubxml`
- Create: `E:\notebook\scripts\publish-skill-manager.ps1`
- Create: `C:\Users\ZS\Desktop\Codex Skill Manager.lnk`

**Interfaces:**
- Consumes: the finished WPF app from Tasks 1 to 4.
- Produces: a single-file EXE in a publish folder and a desktop shortcut that launches it.

- [ ] **Step 1: Define the publish profile**

Set the publish profile for `win-x64`, self-contained, single-file, trimmed only if the app still launches correctly.

- [ ] **Step 2: Add the publish script**

The script should build, publish, copy the executable to a stable folder, and create or refresh the desktop shortcut.

- [ ] **Step 3: Validate the executable**

Run the published EXE directly and confirm it opens the same polished UI as the development build.

- [ ] **Step 4: Verify the shortcut**

Double-click the desktop shortcut and confirm it launches the published EXE.

- [ ] **Step 5: Commit the packaging layer**

```powershell
git -C E:\notebook add codex-skill-manager-wpf\Properties\PublishProfiles scripts\publish-skill-manager.ps1
git -C E:\notebook commit -m "feat: publish skill manager as desktop exe"
```

## Self-Review

- The plan covers project scaffolding, metadata parsing, UI polish, action handling, and packaging.
- No placeholder text remains in the task steps.
- The file paths are explicit and the responsibilities are split by concern.
- The update flow is explicitly separated from refresh so the user can choose either action.
