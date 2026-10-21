# eReader

## Cross-device accounts

Reading progress is stored in Upstash Redis. Each library is addressed by a
private keyword; anyone who knows that keyword can access the library, so use
a hard-to-guess phrase and keep it private. The keyword is not recoverable.

### Vercel deployment

1. In the Vercel project, add the Upstash Redis integration from the Vercel
	Marketplace and connect it to this project.
2. Confirm the project has these environment variables in the deployment
	environments you use:
	- `UPSTASH_REDIS_REST_URL`
	- `UPSTASH_REDIS_REST_TOKEN`
	- `DRIVE_API_KEY` (required to list and proxy Google Drive files)
3. Redeploy the project after adding or changing environment variables. A
	connected Git repository can redeploy on push, or deploy with `vercel --prod`.

For local development, set the same environment variables before starting the
Flask app. Without the two Upstash variables, account creation and restore
return an account-storage configuration error; the existing local browser cache
continues to work.

## Covers

The bookshelf asks `/api/cover?title=...`, which looks the book up on Open
Library, then Google Books, and returns the image. If neither has it (404),
the browser renders the book's own first page instead: page 1 of a PDF, or the
cover image inside an EPUB. Results are cached in the browser (IndexedDB), so
each book is looked up once. No API keys are needed.

## Reader

- Layouts: two pages, single page (fits the screen height) and fit to width
  (default). The choice applies to PDF and EPUB and is remembered.
- EPUBs are downloaded in 3 MB Range chunks and opened from memory, which
  avoids serverless response size limits.
- Appearance: light / dark / auto plus seven colour themes, stored in
  `localStorage` (`readerMode`, `readerPalette`).

## Checks

Run the focused API tests with:

```sh
python -m unittest discover -s tests
```