# UNSC Metadata Backend

国連安保理関連文書の**検索用メタデータ**を登録・修正し、公開フロントエンド向けの JSON を生成するローカル管理ツールです。

このツールが管理するのは以下です。
- 国連ページへの外部リンク
- 決議番号、日付、タイトルなどの基本情報
- 地理的対象、カテゴリ、構造化タグ
- カテゴリ別属性（Sanctions / UN peace operations / Non-UN operations など）
- 後から追加したい項目（`data/schema_overrides.json` で定義）

このツールが**管理しない**ものは以下です。
- 国連文書本文
- PDF ファイルそのもの
- 公開フロントエンド
- API サーバー

---

## 何をどうすれば動くか

### 1. zip を展開してプロジェクトに移動する

```bash
unzip unsc_backend_impl_extensible.zip
cd unsc_backend
```

### 2. Python を確認する

```bash
python --version
```

`3.11` 以上で実行してください。

### 3. 依存関係を入れる

```bash
pip install -r requirements.txt
```

### 4. アプリを起動する

```bash
streamlit run app.py
```

### 5. ブラウザで使う

起動後に表示される URL をブラウザで開きます。通常は以下です。

```text
http://localhost:8501
```

---

## 使い方

### 新規レコードを作る
1. 画面上部の **新規作成** を押す
2. General を入力する
3. 必要なら Sanctions / UN peace operations / Non-UN operations のブロックを追加する
4. 最後に **保存** を押す

### 既存レコードを編集する
1. 画面上部のプルダウンから対象レコードを選ぶ
2. **選択読込** を押す
3. 内容を修正する
4. **保存** を押す

### 公開側 JSON を再生成する
- 画面上部の **公開JSON再生成** を押す
- 保存時にも自動で再生成されます

---

## 保存ファイル

### `data/records.json`
内部管理用の正本です。登録・修正内容はこのファイルに保存されます。

### `data/public_records.json`
公開フロントエンド向けの派生ファイルです。`records.json` から自動生成されます。

### `data/schema_overrides.json`
**後から追加したい項目**を定義するファイルです。ここを編集すると、管理画面にも公開用 JSON にも反映されます。

---

## フォーム構造を後から変更したい場合

固定フォーム本体は Excel 準拠のままにし、**追加分だけ** `data/schema_overrides.json` に書きます。

対応している追加項目の型は以下です。
- `text`
- `textarea`
- `int`
- `bool`
- `date`
- `select`
- `multiselect`

### 追加できる場所
- `general`
- `sanctions`
- `un_peace_operations`
- `non_un_operations_enforcement_actions`
- `criminal_tribunals`
- `other_subsidiary_organs`
- `thematic_resolutions`
- `membership`
- `appointment_related`
- `other`

### 例

```json
{
  "categories": {
    "general": [
      {
        "key": "document_series",
        "label": "Document series",
        "type": "text",
        "required": false,
        "searchable": true
      }
    ],
    "sanctions": [
      {
        "key": "regime_name",
        "label": "Regime name",
        "type": "select",
        "options": ["Libya", "Sudan", "Yemen"],
        "required": false,
        "searchable": true
      }
    ]
  }
}
```

### ルール
- `key` は `snake_case` にしてください
- `select` / `multiselect` は `options` が必須です
- `searchable: true` にすると、その値が `public_records.json` の `tag_filters` に入ります
- `sanctions` / `un_peace_operations` / `non_un_operations_enforcement_actions` に追加した項目は、各ブロックごとに入力します

---

## 実装方針

- 保存形式: JSON
- 管理画面: Streamlit
- 固定フォーム: `form_spec.py` と `masters.py`
- 追加項目: `data/schema_overrides.json`
- 公開側連携: `public_records.json` を渡す
- 削除専用 UI: 実装しない

誤登録時は、管理者が `data/records.json` を手で修正・削除する前提です。

---

## ファイル構成

```text
app.py                  # Streamlit 管理画面
form_spec.py            # 固定フォーム仕様とデフォルト構造
masters.py              # Excel 由来の選択肢定数
schema_overrides.py     # schema_overrides.json の読込・検証
custom_fields.py        # 追加項目の初期化・正規化・タグ抽出
validators.py           # 保存前バリデーションと正規化
storage.py              # records.json / public_records.json / schema_overrides.json の読み書き補助
export_public.py        # 公開側 JSON の生成
data/
  records.json          # 内部管理用正本
  public_records.json   # 公開側受け渡し用
  schema_overrides.json # 追加項目定義
```

---

## 入力上の注意

- `UN document URL` は必須です
- `Resolution number` は必須です
- `Date` は必須です
- `Resolution title` は必須です
- 日付は `YYYY-MM-DD` または `DD/MM/YYYY` で入力してください
- `Sanctions` / `UN peace operations` / `Non-UN operations` は複数ブロック追加できます
- `Modified resolution` や `time period` は条件分岐入力です
- `schema_overrides.json` が壊れているとアプリは起動時に止まります

---

## バージョン固定

- Python: `.python-version` に `3.11` を記載
- Streamlit: `requirements.txt` で `streamlit==1.39.0` に固定
