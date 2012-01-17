#!/usr/bin/env python

"""
Script for migrating issues from Google Code Project Hosting issue trackers to
Github issue trackers.

To use: edit the variables at the top of main() so they have your desired
source and target projects, and also your usernames and passwords for both
sites.
"""
__author__ = "Alex Rudnick (alex.rudnick@gmail.com)"

from __future__ import print_function

import os

import gdata.projecthosting.client
import gdata.projecthosting.data
import gdata.gauth
import gdata.client
import atom.http_core
import atom.mock_http_core
import atom.core
import gdata.data

import json
import urllib2
import base64

## Based substantially on live_client_test from the Google Code Project Hosting
## API example, available here.
## http://code.google.com/p/gdata-python-client/ ...
## ... source/browse/tests/gdata_tests/projecthosting/live_client_test.py

###
### Code to interact with Google Code Project Hosting
###

def all_open_issues(client, project_name):
    """Retrieve a set of issues in a project. Returns a list of IssueEntry
    objects where the issue is not in closed state."""
    query = gdata.projecthosting.client.Query(max_results=1024*1024)
    feed = client.get_issues(project_name, query=query)

    out = []
    for issue in feed.entry:
        if issue.state.text == "closed":
            continue
        out.append(issue)
    return out

def get_comments_for_issue(client, project_name, issue_id):
    issue_id = issue_id.split('/')[-1]
    query = gdata.projecthosting.client.Query(max_results=1024*1024)
    comments_feed = client.get_comments(project_name, issue_id, query=query)
    out = []

    for comment in comments_feed.entry:
        theauthor = None
        for author in comment.author:
            theauthor = author.name.text
        if comment.content.text:
            out.append((theauthor,
                        comment.content.text,
                        comment.published.text))
    return out

def mark_googlecode_issue_migrated(client,
                                   author_name,
                                   project_name,
                                   issue_id,
                                   github_url):
    comment_text = "Migrated to {0}".format(github_url)
    client.update_issue(project_name,
                        issue_id,
                        author=author_name,
                        comment=comment_text,
                        status='Migrated')

###
### Code to interact with Github
###

def create_github_issue(title, body):
    d = {}
    d["title"] = title
    d["body"] = body
    data = json.dumps(d)
    return data

def github_create_issue_url(organization, repo):
    return ("https://api.github.com/repos/{0}/{1}/issues"
            .format(organization, repo))

def post_to_github(url, data, username, password):
    req = urllib2.Request(url, data)
    req.add_header("Authorization", "Basic "
        + base64.urlsafe_b64encode("%s:%s" % (username, password)))
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")

    f = urllib2.urlopen(req)
    response = f.read()
    return json.loads(response)

def post_issue_to_github(title, body, organization, project, user, password):
    """Create a new issue on github. Returns the number (as text) of the new
    issue."""
    uri = github_create_issue_url(organization, project)
    data = create_github_issue(title, body)
    res = post_to_github(uri, data, user, password)
    return res["number"]

###
### Main and utils.
###

def build_previous_comments(comments):
    """Takes a list of tuples of (author, content, published), where they're
    all strings. Produces some HTML to append to an issue's text."""
    out = ""
    if comments:
        out = u"""<hr/><h2>earlier comments</h2>\n"""

    for (author, content, published) in comments:
        out += (u"<p><strong>{0} said, at {1}:</strong></p>\n"
                .format(author,published))
        out += u"<p>{0}</p>".format(content)
    return out

def main():
    ### The Google Code source project
    source_project = "nltk"

    ### Github target project
    github_organization = "nltk"
    github_project = "nltk"

    ### Github username and password
    username, password = 'yourusername','yourgithubpassword'

    ### Usernames and passwords for Google Code
    google_username = 'YOURUSERNAME@gmail.com'
    google_password = 'yourgooglepassword'
    google_name = "your.displayname"

    application_name = 'project hosting issue migrator'
    client = gdata.projecthosting.client.ProjectHostingClient()
    client.ClientLogin(google_username, google_password, source=application_name)

    issues = all_open_issues(client, source_project)

    for issue in issues:
        print("Migrating", issue.id.text)
        comments = get_comments_for_issue(client, source_project, issue.id.text)
        prevcomments = build_previous_comments(comments)

        source_issue_id = issue.id.text.split('/')[-1]

        migrated_from = (
          u"<p>Migrated from http://code.google.com/p/{0}/issues/detail?id={1}</p>".
          format(source_project, source_issue_id))

        newtext = issue.content.text + migrated_from + prevcomments
        github_issue_id = post_issue_to_github(issue.title.text,
                                               newtext,
                                               github_organization,
                                               github_project,
                                               username,
                                               password)
        new_github_issue_url = ("http://github.com/{0}/{1}/issues/{2}"
                                .format(github_organization,
                                        github_project,
                                        github_issue_id))
        print("Created", new_github_issue_url)
        mark_googlecode_issue_migrated(client,
                                       google_name,
                                       source_project,
                                       source_issue_id,
                                       new_github_issue_url)

if __name__ == "__main__": main()
