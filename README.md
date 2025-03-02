# cloudflare-dynamic-dns
Python script to use Cloudflare for dynamic DNS

## Setup

 1. [Create an A
    record](https://support.cloudflare.com/hc/en-us/articles/360019093151-Managing-DNS-records-in-Cloudflare#h_60566325041543261564371)
    in CloudFlare

 2. [Create an API token](https://developers.cloudflare.com/api/tokens/create)
    with write access to the zone the A record is in.

 3. Run `update.py` to generate a config file and update the A record to your
    current public IP address:

    ```
    $ python update.py
    Auth token: Njk2ZD-I5ZTA5NDBhNDk1Nzc0OGZlM2ZjOWVmZDI
    Zone name: example.com
    A record name: updateme.example.com
    INFO:root:Saving new config to cloudflare-dynamic-dns.json
    INFO:root:Updated updateme.example.com (1.2.3.4)
    ```

 4. Periodically re-run the script (e.g. via cron) to keep the A record
    up-to-date.
