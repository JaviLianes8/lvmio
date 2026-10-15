# Local quality gate. Run before every commit. No CI runs in the cloud.
$ErrorActionPreference = "Stop"

foreach ($step in @(
    @("ruff", "format", "--check", "."),
    @("ruff", "check", "."),
    @("mypy", "--strict", "src", "tests"),
    @("pytest")
)) {
    & $step[0] $step[1..($step.Length - 1)]
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
