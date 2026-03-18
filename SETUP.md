# セットアップ手順

## 前提：Pythonのインストール

### Mac の場合

1. https://www.python.org/downloads/ を開く
2. 「Download Python 3.x.x」ボタンをクリックしてダウンロード
3. ダウンロードされた `.pkg` ファイルをダブルクリックして指示通りにインストール

### Windows の場合

1. https://www.python.org/downloads/ を開く
2. 「Download Python 3.x.x」ボタンをクリックしてダウンロード
3. ダウンロードされた `.exe` ファイルをダブルクリック
4. **「Add python.exe to PATH」にチェックを入れてから** Install Now をクリック

---

## アプリの起動手順

### 1. ファイルを展開する

受け取った zip ファイル（`unsc_backend.zip`）をダブルクリックして展開してください。
`unsc_backend` というフォルダが作成されます。

---

### 2. ターミナル（コマンドプロンプト）を開く

**Mac の場合：**
- `Command + Space` を押して「ターミナル」と入力 → Enter

**Windows の場合：**
- スタートボタンを右クリック →「Windows PowerShell」または「コマンドプロンプト」

---

### 3. フォルダに移動する

ターミナルに以下を入力して Enter：

**Mac の場合（Downloads に展開した場合）：**
```
cd ~/Downloads/unsc_backend
```

**Windows の場合（ダウンロードフォルダに展開した場合）：**
```
cd %USERPROFILE%\Downloads\unsc_backend
```

---

### 4. 必要なライブラリをインストールする（初回のみ）

以下を入力して Enter：
```
pip install -r requirements.txt
```

数十秒〜数分かかります。完了したら次へ進んでください。

---

### 5. アプリを起動する

以下を入力して Enter：
```
streamlit run app.py
```

しばらくするとブラウザが自動で開き、アプリが表示されます。

ブラウザが開かない場合は、手動でブラウザのアドレスバーに以下を入力してください：
```
http://localhost:8501
```

---

## アプリの使い方

アプリ画面の右上にある **Help** ボタンをクリックすると、日本語・英語の操作説明が表示されます。

---

## アプリを終了するには

ターミナルで `Ctrl + C` を押してください。

---

## テストデータについて

このファイルにはテストデータ（106件）が入っています。
本番運用を開始する前に、以下のファイルをテキストエディタで開いて中身を `[]` に書き換えて保存してください：

- `data/records.json`
- `data/public_records.json`

書き換え後のファイルの中身：
```
[]
```
