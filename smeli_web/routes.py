from smeli_web import smeli_app
from flask import render_template, request, url_for, redirect, current_app, session, jsonify
from smeli.sources import get_paper_candidates


@smeli_app.route("/")
def index():
    return render_template("info.html")

@smeli_app.route("/smeli")
def smeli():
    return render_template("smeli.html")

@smeli_app.route("searchfilter")
def search_filter():
    lookup_criteria = dict()
    for criteria in { 'author', 'title', 'year', 'identified' }:
        if criteria in request.args:
            lookup_criteria[criteria] = request.args[criteria]

    if !lookup_criteria:
        return render_template("searchFilter.html", data=None)
    candidates = get_paper_candidates( **lookup_criteria )
    return render_template("searchFilter.html", data=candidates)

@smeli_app.route("/api/lookup")
def lookup():
    lookup_criteria = dict()
    for criteria in { 'author', 'title', 'year', 'identified' }:
        if criteria in request.args:
            lookup_criteria[criteria] = request.args[criteria]

    candidates = get_paper_candidates( **lookup_criteria )
    return jsonify(candidates)

