"""Shared preprocessing helpers."""


def clean_column_names(columns):
    return [col.strip().lower().replace(" ", "_") for col in columns]
