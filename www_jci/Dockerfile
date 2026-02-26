FROM	alpine:latest
RUN 	apk add --no-cache git ca-certificates stagit
WORKDIR /work
ADD 	./ /tmp
RUN mkdir /gitrepo  \
    && (cd /tmp/repo && ls -alR /tmp && head README.md | grep '>' > description)  \
    && stagit -u /git /tmp/repo  \
    && rm /tmp/repo/description  \
    && cp /tmp/repo/www_jci/public/assets/git.style.css /gitrepo/style.css  \
    && cp /tmp/repo/www_jci/public/assets/logo.png /gitrepo/logo.png  \
    && cp /gitrepo/logo.png /gitrepo/favicon.png
CMD ["/bin/sh"]
