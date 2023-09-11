import streamlit as st
import pandas as pd
import re
from github import Github, Auth
import plotly.express as px

UNKNOWN_VALUE = "unknown"


def email_to_domain_name(email):
    if email is None:
        return UNKNOWN_VALUE
    match = re.search(r'.+@(.+)', email)
    if match:
        return match.group(1)
    return UNKNOWN_VALUE


def get_orgs(user):
    orgs = set(org.name for org in user.get_orgs()
               if org.name is not None and org.name != "")

    if len(orgs) == 0:
        orgs = set([UNKNOWN_VALUE])

    return list(orgs)


@st.cache_data
def contributors_df(token, repository):
    g = Github(auth=Auth.Token(token)) if token != "" else Github()

    repo = g.get_repo(repository)

    contributors = [user for user in repo.get_contributors()]

    return pd.DataFrame({
        "name": [user.name for user in contributors],
        "domain": [email_to_domain_name(user.email) for user in contributors],
        "org": [get_orgs(user) for user in contributors]
    })


def truncate_topk(df, topk, key_column, value_column, truncation_label):
    topk_values = df.nlargest(topk, value_column, keep="last")
    if len(topk_values) == 0:
        return topk_values

    threshold = topk_values[value_column].min()

    df = df.copy()
    df.loc[df[value_column] < threshold, key_column] = truncation_label

    return df


def plot_group_by_domain(df, topk, ignore_unknown):
    if ignore_unknown:
        df = df.loc[df["domain"] != UNKNOWN_VALUE]

    grouped_by_domain = df.groupby("domain").size().reset_index(name="count")

    grouped_by_domain_topk = truncate_topk(
        grouped_by_domain, topk, "domain", "count", "others")

    fig = px.pie(grouped_by_domain_topk, values="count", names="domain",
                 title='Distribution of contributor email domain')

    st.plotly_chart(fig, use_container_width=True)


def plot_group_by_org(df, topk, ignore_unknown):
    exploded_by_org = df.explode("org")

    if ignore_unknown:
        exploded_by_org = exploded_by_org.loc[exploded_by_org["org"]
                                              != UNKNOWN_VALUE]

    grouped_by_org = exploded_by_org.groupby(
        "org").size().reset_index(name="count")

    grouped_by_org_topk = truncate_topk(
        grouped_by_org, topk, "org", "count", "others")

    fig = px.pie(grouped_by_org_topk, values="count", names="org",
                 title='Distribution of contributor organization')

    st.plotly_chart(fig, use_container_width=True)


st.write("""
# GitHub Contributor Analysis
""")

with st.sidebar:
    topk = st.number_input('The top-k values to show', 1, 20, 10)

    ignore_unknown = st.toggle("Ignore unknown value", value=False)

st.text_input("Please input the repository in owner/repo format",
              key="repo", value="google/leveldb")

df = contributors_df(st.secrets["github_token"], st.session_state.repo)

plot_group_by_domain(df, topk=topk, ignore_unknown=ignore_unknown)

plot_group_by_org(df, topk=topk, ignore_unknown=ignore_unknown)
