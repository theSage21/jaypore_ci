"""
An email remote.

This is used to report pipeline status via email.
Multiple updates appear as a single thread.
"""
import os
import time
import smtplib
from html import escape as html_escape

from email.headerregistry import Address
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlparse


from jaypore_ci.interfaces import Remote, Repo
from jaypore_ci.logging import logger


class Email(Remote):  # pylint: disable=too-many-instance-attributes
    """
    You can send pipeline status via email using this remote. In order to use it you
    can specify the following environment variables in your secrets:

    .. code-block:: console

        JAYPORE_EMAIL_ADDR=email-account@gmail.com
        JAYPORE_EMAIL_PASSWORD=some-app-password
        JAYPORE_EMAIL_TO=myself@gmail.com,mailing-list@gmail.com
        JAYPORE_EMAIL_FROM=noreply@gmail.com

    If you're using something other than gmail, you can specify
    `JAYPORE_EMAIL_HOST` and `JAYPORE_EMAIL_PORT` as well.

    Once that is done you can supply this remote to your pipeline instead of
    the usual gitea one.

    .. code-block:: python

        from jaypore_ci import jci, remotes, repos

        git = repos.Git.from_env()
        email = remotes.Email.from_env(repo=git)
        with jci.Pipeline(repo=git, remote=email) as p:
            pass
            # Do something

    :param host: What smtp host to use.
    :param port: Smtp port to use.
    :param addr: Smtp address to use for login.
    :param password: Smtp password to use for login.
    :param email_to: Which address the email should go to.
    :param email_from: Which address should be the sender of this email.
    :param subject: The subject line of the email.
    :param only_on_failure: If set to True, a single email will be sent when
                            the pipeline fails. In all other cases no email is
                            sent.
    :param publish_interval: Determines the delay in sending another email when
                             we are sending multiple email updates in a single
                             email thread. If `only_on_failure` is set, this
                             option is ignored.
    """

    @classmethod
    def from_env(cls, *, repo: Repo) -> "Email":
        """
        Creates a remote instance from the environment.
        """
        remote = urlparse(repo.remote)
        owner = Path(remote.path).parts[1]
        name = Path(remote.path).parts[2].replace(".git", "")
        return cls(
            host=os.environ.get("JAYPORE_EMAIL_HOST", "smtp.gmail.com"),
            port=int(os.environ.get("JAYPORE_EMAIL_PORT", 465)),
            addr=os.environ["JAYPORE_EMAIL_ADDR"],
            password=os.environ["JAYPORE_EMAIL_PASSWORD"],
            email_to=os.environ["JAYPORE_EMAIL_TO"],
            email_from=os.environ.get(
                "JAYPORE_EMAIL_FROM", os.environ["JAYPORE_EMAIL_ADDR"]
            ),
            subject=f"JCI [{owner}/{name}] [{repo.branch} {repo.sha[:8]}]",
            branch=repo.branch,
            sha=repo.sha,
        )

    def __init__(
        self,
        *,
        host: str,
        port: int,
        addr: str,
        password: str,
        email_to: str,
        email_from: str,
        subject: str,
        only_on_failure: bool = False,
        publish_interval: int = 30,
        **kwargs,
    ):  # pylint: disable=too-many-arguments
        super().__init__(**kwargs)
        # --- customer
        self.host = host
        self.port = port
        self.addr = addr
        self.password = password
        self.email_to = email_to
        self.email_from = email_from
        self.subject = subject
        self.timeout = 10
        self.publish_interval = publish_interval
        self.only_on_failure = only_on_failure
        # ---
        self.__smtp__ = None
        self.__last_published_at__ = None
        self.__last_report__ = None

    @property
    def smtp(self):
        if self.__smtp__ is None:
            smtp = smtplib.SMTP_SSL(self.host, self.port)
            smtp.ehlo()
            smtp.login(self.addr, self.password)
            self.__smtp__ = smtp
        return self.__smtp__

    def logging(self):
        """
        Return's a logging instance with information about gitea bound to it.
        """
        return logger.bind(addr=self.addr, host=self.host, port=self.port)

    def publish(self, report: str, status: str) -> None:
        """
        Will publish the report via email.

        :param report: Report to write to remote.
        :param status: One of ["pending", "success", "error", "failure",
            "warning"] This is the dot next to each commit in gitea.
        """
        assert status in ("pending", "success", "error", "failure", "warning")
        if (
            self.__last_published_at__ is not None
            and (time.time() - self.__last_published_at__) < self.publish_interval
            and status not in ("success", "failure")
        ) or (self.only_on_failure and status != "failure"):
            return
        if self.__last_report__ == report:
            return
        self.__last_report__ = report
        self.__last_published_at__ = time.time()
        # Let's send the email
        msg = EmailMessage()
        msg["Subject"] = self.subject
        msg["From"] = Address("JayporeCI", "JayporeCI", self.email_from)
        msg["To"] = self.email_to
        msg.set_content(report)
        msg.add_alternative(
            f"<html><body><pre>{html_escape(report)}</pre></body></html>",
            subtype="html",
        )
        try:
            self.smtp.send_message(msg)
        except Exception as e:  # pylint: disable=broad-except
            self.logging().exception(e)
        self.__last_published_at__ = time.time()
        self.logging().info(
            "Report published",
            subject=self.subject,
            email_from=self.email_from,
            email_to=self.email_to,
        )
