# Databricks notebook source
# Control Tower — follow-up notification carrier.
# The app submits this as a one-time serverless run with email_notifications.on_success = [recipient];
# Databricks emails the recipient when it finishes. The run output shows the full follow-up message.
dbutils.widgets.text("title", "")
dbutils.widgets.text("message", "")
title, message = dbutils.widgets.get("title"), dbutils.widgets.get("message")
print(title)
print(message)
dbutils.notebook.exit(f"{title}\n{message}")
