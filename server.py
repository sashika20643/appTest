from flask import Flask, render_template, request, redirect, url_for
import boto3

app = Flask(__name__)

S3_BUCKET = 'social-lips'
S3_ACCESS_KEY = 'AKIATVMCFFMCIUHMGIXF'
S3_SECRET_KEY = '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'

s3_client = boto3.client(
    's3',
    aws_access_key_id=S3_ACCESS_KEY,
    aws_secret_access_key=S3_SECRET_KEY
)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    s3_client.upload_fileobj(file, S3_BUCKET, file.filename)
    return redirect(url_for('index'))

@app.route('/download/<filename>')
def download(filename):
    s3_client.download_file(S3_BUCKET, filename, filename)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
