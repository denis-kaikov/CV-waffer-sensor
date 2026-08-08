# AGENTS.md

## Project context

This is a Windows .NET application written in C#.

Prefer small, targeted changes. Do not scan the whole repository unless needed. Before editing, identify the relevant project, solution, and files.

## Token discipline

- Use narrow searches: `rg "term" -n` instead of reading many files.
- Do not paste full build logs into the conversation. Summarize the first relevant error and inspect only the files involved.
- Prefer minimal command output:
  - `dotnet build --nologo -v:minimal`
  - `dotnet test --nologo -v:minimal --logger "console;verbosity=minimal"`
  - `dotnet restore --nologo`
- Run `dotnet restore` only after changing project files, NuGet packages, or `Directory.Packages.props`.
- Do not run broad commands like recursive directory dumps unless explicitly needed.
- Before large refactors, propose a short plan and list the files to change.

## .NET coding rules

- Use modern C# style.
- Keep nullable reference types clean when enabled.
- Prefer dependency injection over service locators.
- Avoid blocking async code with `.Result` or `.Wait()`.
- Avoid doing long-running work on the UI thread.
- Keep public APIs small and documented when behavior changes.
- Add or update tests when changing logic.

## Windows desktop rules

- For WPF/WinUI/WinForms UI changes, keep UI logic separated from business logic.
- Prefer MVVM-style separation for WPF/WinUI where practical.
- Do not introduce new UI frameworks or heavy dependencies without asking.
- Preserve existing project structure and naming conventions.

## Validation

After code changes, run the narrowest useful validation first:

1. `dotnet build --nologo -v:minimal`
2. Relevant test project only, if tests exist.
3. Full solution tests only when necessary.