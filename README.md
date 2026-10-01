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

- 登録バージョン: [Cask の version](Casks/mizu-pairrank.rb) を参照
- 対応: macOS / Apple Silicon（ARM64）
- 配布元: [mizu-pairrank の Releases](https://github.com/mizucopo/mizu-pairrank/releases)
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
自動連携の設定・有効化後は、配布元の安定版 Release 完了通知を受けて Tap が配布 ZIP を検証し、Cask のバージョンと SHA-256 を自動更新します。
設定状況、検証内容、失敗時の再実行、アプリの追加方法は[自動更新の運用手順](automation/README.md)を参照してください。
連携が未設定・停止中の場合は、下記の手順で手動更新できます。

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
6. 対応アプリの追加時はこの README と自動更新の登録を更新して Pull Request を作成します。

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
