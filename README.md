# dme-update

## Python-based DNS Made Easy Updater in Docker Container

**Please Note**: I'm not planning on updating this container any longer. Its functionality has been merged into another tool I built that handles DDNS updates for Cloudflare, DNS Made Easy, or DNS-O-Matic. You can find that one at [jcostom/ddnsup](https://github.com/jcostom/ddnsup).

So, for the past many years, I've been leveraging DNS-o-Matic for doing multiplexing DDNS updates over a handful of things, including updating a couple of A records inside DNS Made Easy. Over the years, DNS-o-Matic has had a handful of flake-outs on me. Over the past year, that number has increased. To the point where it's grown to be annoying. I'm not sure if I'm just "special" or if others see it too, but sometimes, my updates just go off into la-la land.

So, it was enough to get me to read up on DNS Made Easy's API, and write my very own updater, and here we are. Lots of code from the jcostom/dnsomatic-update project got forklifted straight into this.

You've got a sample docker-compose file in the repository already. Have a look. It's useful if you're the Compose or Portainer type. If you're the launch-it-yourself from the CLI type, here's an example of how you might do that as well...

```bash
docker run -d \
    --name=dme \
    --user 1000:1000 \
    --restart=unless-stopped \
    -v /var/docks/dme:/config \
    -e APIKEY=24681357-abc3-12345-a1234-987654321 \
    -e SECRETKEY=123456-ab123-123ab-9876-123456789 \
    -e DMEZONEID=123456 \
    -e RECORDS=host1,host2 \
    -e USETELEGRAM=1 \
    -e CHATID=0 \
    -e MYTOKEN=1111:1111-aaaa_bbbb.cccc \
    -e SITENAME='HOME' \
    -e TZ='America/New_York' \
    jcostom/dme-update
```

If you decide to not use Telegram for notifications, set the USETELEGRAM variable to 0, and then you can leave out the CHATID, MYTOKEN, and SITENAME variables.

Creating a Telegram bot is fairly well documented at this point and is beyond the scope of this README. Have a read up on that, get your bot token, get your chat ID, and you're ready to roll.

Optionally, if you're having trouble, and want to do some debugging, set the DEBUG=1 variable. As of version 1.2, you can set the variable, and now that I've transitioned to the Python logging module, you get decent debug logging in the standard container log output. Just look at the regular output of `docker logs container-name`.
