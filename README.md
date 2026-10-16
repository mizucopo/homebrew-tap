# homebrew-tap

mizucopo の CLI とデスクトップアプリを Homebrew でインストールするための Tap です。
CLI は `Formula/<名前>.rb`、デスクトップアプリは `Casks/<名前>.rb` で管理します。

## game-screen-pick（CLI）

ゲーム録画から画像を抽出・選定する CLI です。公開済みの安定版 binary を使うため、Rust toolchain は不要です。

| 環境 | 対応・前提条件 |
| --- | --- |
| macOS / Apple Silicon ARM64 | macOS 14 (Sonoma) 以降かつ Homebrew の対応環境。配布元の最低 OS 宣言は14、Tap での導入・更新・画像抽出は macOS 27 ARM64で確認 |
| Linux / x86_64 GNU | Ubuntu 22.04相当以降（glibc 2.35以降、libgcc、標準 dynamic loader）かつ Homebrew の対応環境。配布物の完全性・ELF/CPU は確認済み。Linux 上の Tap 経由の導入・更新は未検証 |
| Intel Mac / Linux ARM64 / Windows | この Formula の対象外。Windows は配布元の Releases を参照 |

- パッケージ名（pc-setup 向け）: `mizucopo/tap/game-screen-pick`（Formula）
- 登録版: [Formula の固定 URL](Formula/game-screen-pick.rb)（`brew info mizucopo/tap/game-screen-pick` でも確認可能）。OS 別の固定 URL と SHA-256 でダウンロードを検証します
- 実行時の `ffmpeg` と `ffprobe` は Homebrew の `ffmpeg` 依存として導入します。日本語 font は binary に含まれます
- AI による選定には、画像・動画能力を確認した推論 endpoint、model、認証・設定が別途必要です。推論なしの `extract` も利用できます

```sh
brew tap mizucopo/tap
brew install --formula mizucopo/tap/game-screen-pick
game-screen-pick --version
game-screen-pick --help
brew test mizucopo/tap/game-screen-pick
```

設定例は `$(brew --prefix)/share/game-screen-pick/config.example.toml` にあります。
利用者の既存設定を上書きしない新しい名前へコピーし、[本体の利用案内](https://github.com/mizucopo/game-screen-pick#設定して実行)に沿って接続先を設定します。
利用文書・build/依存情報は `$(brew --prefix)/share/doc/game-screen-pick/`、license 資料は `$(brew --prefix game-screen-pick)/licenses/` に残します。

更新・削除は次のとおりです。設定・録画・出力・cache は利用者の作業ディレクトリで管理し、Formula は変更しません。

```sh
brew update
brew upgrade --formula mizucopo/tap/game-screen-pick
game-screen-pick --version
brew test mizucopo/tap/game-screen-pick
# 削除する場合
brew uninstall --formula mizucopo/tap/game-screen-pick
```

更新先はこの Tap の登録版です。CLI の次回 Release は `livecheck` で検出し、配布物を検証した更新 PR で追従します。
既存 Cask の自動更新とは独立した手動レビュー運用です。[Formula の保守手順](automation/README.md#cli-formula-の更新)を参照してください。

## mizu-pairrank（デスクトップアプリ）のインストール

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
