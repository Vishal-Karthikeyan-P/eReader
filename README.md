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

## Checks

Run the focused API tests with:

```sh
python -m unittest discover -s tests
```