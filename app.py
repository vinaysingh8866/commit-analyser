import plotly.graph_objects as go
from flask import Flask, render_template, request, send_from_directory
import base64
import io
import matplotlib.pyplot as plt
import requests
from bs4 import BeautifulSoup
import pandas as pd
import openai


import os
openai.api_key = os.getenv("OPENAI_API_KEY")



def get_commit_counts_from_svg(username):
    base_url = f'https://github.com/{username}'
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')

    contribution_graph = soup.select_one('svg.js-calendar-graph-svg')

    daily_commit_counts = {}
    for rect in contribution_graph.select('rect.ContributionCalendar-day'):
        date = rect['data-date']
        text = rect.text
        if "No contributions" in text:
            count = 0
        else:
            count = int(text.split(" ")[0])

        daily_commit_counts[date] = count
    df = pd.DataFrame.from_dict(
        daily_commit_counts, orient='index', columns=['count'])
    df.index = pd.to_datetime(df.index)
    df['day_of_week'] = df.index.day_name()
    df = df.groupby('day_of_week').sum()
    df = df.reindex(['Monday', 'Tuesday', 'Wednesday',
                    'Thursday', 'Friday', 'Saturday', 'Sunday'])
    daily_commit_counts = df['count'].to_dict()
    return daily_commit_counts


app = Flask(__name__)


def plot_commit_counts(commit_counts):
    days = list(commit_counts.keys())
    counts = list(commit_counts.values())

    # Customize the bar colors
    bar_colors = ['#2c7bb6', '#00a6ca', '#00ccbc',
                  '#90eb9d', '#ffff8c', '#fdae61', '#d7191c']

    fig = go.Figure(go.Bar(
        x=days,
        y=counts,
        marker_color=bar_colors,
        text=counts,
        textposition='outside'
    ))

    fig.update_layout(
        title=dict(
            text="GitHub Commits ",
            font=dict(size=24),
            pad=dict(t=30)
        ),
        xaxis=dict(
            title="Day of Week",
            titlefont=dict(size=18),
            tickfont=dict(size=14),
        ),
        yaxis=dict(
            title="Number of Commits",
            titlefont=dict(size=18),
            tickfont=dict(size=12),
            gridcolor='gray',
            gridwidth=0.5
        ),
        plot_bgcolor='white'
    )

    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='gray')

    # Remove the frame
    fig.update_xaxes(showgrid=False, showline=True, linewidth=0.5)
    fig.update_yaxes(showgrid=True, showline=False, linewidth=0.5)

    return fig.to_html(include_plotlyjs='cdn', full_html=False)


def split_text(text):
    parts = text.split(': ')
    productive_day = parts[1].split(' ')[0]
    least_productive_day = parts[3].split(' ')[0]
    tagline = parts[5]
    return productive_day, least_productive_day, tagline


def get_interpretation(commit_counts):
    commit_counts_str = "\n".join(
        [f"{day}: {count}" for day, count in commit_counts.items()])
    print(commit_counts_str)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content":
             commit_counts_str +
             """Make cool interpretation from my github commits based on the data above. and give me a response in a tag line like
            You are a weekend warrior! You do most of your work on the weekends
            Reply only this do not add anything else to the response.
             """},
        ]
    )

    interpretation = response.choices[0].message['content']
    return interpretation


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        username = request.form['username']
        commit_counts = get_commit_counts_from_svg(username)
        
        tagline = get_interpretation(commit_counts)
        profuctive_day = max(commit_counts, key=commit_counts.get)
        least_productive_day = min(commit_counts, key=commit_counts.get)
        chart = plot_commit_counts(commit_counts)
        
        return render_template('index.html', chart=chart, username=username, profuctive_day=profuctive_day, least_productive_day=least_productive_day, tagline=tagline)
    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
