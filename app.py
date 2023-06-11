from bs4 import BeautifulSoup
from whoosh.fields import Schema, ID, TEXT
from flask import Flask, request, render_template, send_from_directory
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser
import os

popular_searches = {}
search_history = []
app = Flask(__name__)

def search(query, index_dir='indexdir'):
    ix = open_dir(index_dir)
    with ix.searcher() as searcher:
        query_parser = QueryParser("content", ix.schema)
        parsed_query = query_parser.parse(query)
        results = searcher.search(parsed_query, limit=None)
        return [(result['path'], result.highlights("content")) for result in results]


@app.route('/')
def index():
    return render_template('index.html', search_history=search_history, popular_searches=sorted(popular_searches.items(), key=lambda x: x[1], reverse=True)[:10])

@app.route('/browse')
def browse_files():
    file_tree = generate_file_tree('files')
    return render_template('browse.html', file_tree=file_tree)


def generate_file_tree(base_dir):
    file_tree = {}
    for root, dirs, files in os.walk(base_dir):
        group_name = os.path.relpath(root, base_dir)
        file_tree[group_name] = []
        for file in files:
            if file.endswith('.html'):
                file_tree[group_name].append(os.path.join(group_name, file))
    return file_tree


@app.route('/browse/<path:filepath>')
def browse(filepath):
    return send_from_directory('files', filepath)


@app.route('/search')
def search_results():
    query = request.args.get('q', '')

    if query:
        search_history.append(query)
        if len(search_history) > 10:
            search_history.pop(0)

        # Update the popular searches dictionary
        if query in popular_searches:
            popular_searches[query] += 1
        else:
            popular_searches[query] = 1

    results = search(query)
    return render_template('index.html', search_history=search_history, search_results=results, popular_searches=sorted(popular_searches.items(), key=lambda x: x[1], reverse=True)[:10])


def index_html_files(base_dir, index_dir='indexdir'):
    schema = Schema(path=ID(unique=True, stored=True),
                    content=TEXT(stored=True))
    if not os.path.exists(index_dir):
        os.mkdir(index_dir)
    ix = create_in(index_dir, schema)
    writer = ix.writer()

    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    soup = BeautifulSoup(f, 'html.parser')
                    text = soup.get_text()
                    writer.add_document(path=file_path, content=text)
    writer.commit()


if __name__ == '__main__':
    index_html_files("files")
    app.run(debug=True)
