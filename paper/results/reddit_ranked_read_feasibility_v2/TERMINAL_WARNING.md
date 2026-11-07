# Terminal warning retained after the v2 positive control

The v2 control's official HAR grader passed and the POST received HTTP 200. The
process also printed `Task exception was never retrieved` from Playwright's
`Response.finished` background `on_finished` task when the browser closed; the
task raised `Error('Target closed')`. The version pinned in the v2 seal is the
browser-boundary Python 3.13 environment. Its `Response.finished` implementation
creates a task waiting for target closure and does not cancel that task when the
response completes. This terminal output is not represented in `record.json`, so
the v2 `all_passed` field covers its recorded grader assertions only and is **not
a clean-run decision**. The complete terminal warning is retained in this file
alongside the immutable v2 archive. Version 3 removes the `finished()` call and
requires the response body before closing the owned browser context.
