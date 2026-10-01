# homebrew-tap

mizucopo のデスクトップアプリを Homebrew でインストールするための Tap です。
アプリごとに `Casks/<アプリ名>.rb` を追加して管理します。

## インストール

[Homebrew](https://brew.sh/) が利用できる Apple Silicon Mac で実行します。

```sh
brew tap mizucopo/tap
brew install --cask mizucopo/tap/mizu-pairrank
```

### mizu-pairrank

ふたつの項目を比べて、自分の好みのランキングを作るデスクトップアプリです。

- 登録バージョン: 0.7.0
- 対応: macOS / Apple Silicon（ARM64）
- 配布元: [mizu-pairrank の Releases](https://github.com/mizucopo/mizu-pairrank/releases/tag/0.7.0)
- インストールするアプリ: `mizu-pairrank.app`

このバージョンの macOS アプリは ad-hoc 署名で、Apple の公証は行っていません。
Homebrew で配置できても、起動時に macOS Gatekeeper によってブロックされる場合があります。
この Tap は隔離属性の削除や Gatekeeper の無効化を行いません。

Intel Mac 向けの macOS アセットはありません。Windows 向け ZIP は配布元の Releases から取得できます。

## アップデート

アプリを終了してから実行します。

```sh
brew update
brew upgrade --cask mizucopo/tap/mizu-pairrank
```

更新はこの Tap の Cask に登録されているバージョンへ行われます。
配布元で新しい Release を公開しただけでは Cask は更新されないため、下記の手順でバージョンと SHA-256 を更新します。

## アンインストール

```sh
brew uninstall --cask mizucopo/tap/mizu-pairrank
```

保存データを削除する `zap` は定義していません。
mizu-pairrank の保存先とバックアップ方法は[アプリの README](https://github.com/mizucopo/mizu-pairrank#保存とアップデート)を参照してください。

## Cask の追加・更新

1. アプリの公開 Release と対象 OS・CPU のアセットを確認します。ダウンロード URL はバージョンを固定します。
2. アセットをダウンロードし、`shasum -a 256 <ファイル名>` で SHA-256 を計算します。
3. ZIP 内の `.app` 名・バージョン・対応 OS・CPU を確認します。
4. 追加時は `Casks/<アプリ名>.rb` を作成します。更新時は既存 Cask の `version`・`sha256` を変更し、URL と `app` が引き続き一致することを確認します。
5. 対応する Mac で下記を実行し、インストールと起動を確認します。既にインストール済みの場合は、データをバックアップしアプリを終了してから更新を確認します。
6. この README の対応アプリ・バージョンを更新して Pull Request を作成します。

```sh
brew style Casks/mizu-pairrank.rb
brew audit --cask --online mizucopo/tap/mizu-pairrank
brew install --cask mizucopo/tap/mizu-pairrank
```

`brew livecheck --cask mizucopo/tap/mizu-pairrank` で配布元の最新 Release を確認できます。
livecheck は Cask の自動更新や公開を行いません。
署名・公証に関する警告や検証失敗は、配布元のアプリで解決してください。

## 参考

- [Homebrew Cask Cookbook](https://docs.brew.sh/Cask-Cookbook)
- [How to Create and Maintain a Tap](https://docs.brew.sh/How-to-Create-and-Maintain-a-Tap)
