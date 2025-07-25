# cyberjackal_mkv/trader_app/wsgi.py
# THIS IS THE OFFICIAL AND ONLY ENTRYPOINT FOR THE GUNICORN WEB SERVER.
# It imports the factory function from our package and creates the app instance.

from trader_app import create_app
import sentry_sdk

# --- Sentry Initialization ---
sentry_sdk.init(
    dsn="https://a44ba399e833b1caf79c3c949610e04d@o4509651104759809.ingest.us.sentry.io/4509651108429824",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions for slow-running code
    profiles_sample_rate=1.0,
)

# The 'app' object that Gunicorn will look for.
# This is the standard way to integrate with WSGI servers.
app = create_app()
