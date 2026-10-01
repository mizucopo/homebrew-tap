# Release-driven Cask updates

## 動作

1. 各アプリの Release ワークフローが、配布ファイルの公開と latest の更新を完了します。
2. 専用 GitHub App の短時間トークンで、この Tap の `update-casks.yml` を `workflow_dispatch` します。
3. Tap が `apps.json` に登録した全アプリの最新の安定版を GitHub API から読み直します。通知元からバージョン・URL・チェックサムを受け取りません。
4. 検証がすべて成功した場合だけ、Cask の `version` と `sha256` を `main` に通常の fast-forward push で反映します。バージョン固定 URL は既存の `#{version}` 補間を使います。

定期実行には依存しません。公開リポジトリの scheduled workflow の非アクティブ停止を避けられますが、GitHub Actions/API の障害や無効化、鍵の失効まで解決するものではありません。通知成功は受付成功であり、Tap の検証・公開成功は Tap 側の実行結果で確認します。

## 検証・安全策

- ソースは `mizucopo` 所有の明示登録リポジトリのみ。現在の対応形式は数値3要素の安定版と、macOS ARM64 の ZIP です
- 公開済み・非 draft・非 prerelease の Release と、完全一致するアセット名・固定 URL・uploaded 状態・サイズ・GitHub の SHA-256 digest を確認します
- ダウンロードした実際のバイト列から SHA-256 を計算し、API の digest と一致させます。ダウンロードに認証ヘッダーを付けず、リダイレクト先は GitHub の既知の配布ホストに制限します
- ZIP を展開・実行せず、パス、重複、リンク、暗号化、展開サイズ、CRC、`.app` 名、bundle ID、アプリ版、ARM64 Mach-O 実行形式を確認します
- 旧版への後退、同一バージョンのアセット差し替え、検証中の Release 変更は自動反映しません。同一版・同一 SHA は何もコミットしません
- 全アプリを検証してから書き込みます。一つでも失敗すれば、その実行では他の Cask も公開しません
- push が競合した場合は最新の main から検証し直します。通常の競合は最大5回まで再試行し、強制 push やブランチ保護の迂回は行いません。実行中に automation または `.github` が変わった場合は止まります
- apply 実行は直列化します。GitHub が待機中の実行をまとめても、毎回全アプリを再確認するためアプリ別の通知を取りこぼしにくい構成です。dry run は apply の待機枠を取りません
- Release のタイトルや本文はコマンド・Cask・コミット文に使用しません
- アプリの署名・公証状態は変更しません。Gatekeeper の無効化や隔離属性の削除も行いません

バージョン固定 URL と SHA は内容の変更を検出しますが、配布元自体の侵害を防ぐ署名検証ではありません。現在の配布元 Release は GitHub の immutable release 設定を必須にしていません。同一版を差し替えず、新しいバージョンで公開してください。

## 初回設定・有効化

ワークフローを main に入れるレビューと、以下の資格情報・権限設定は別の承認が必要です。設定完了まで enable 変数を `true` にしないでください。

1. 個人アカウント `mizucopo` の専用 GitHub App を作り、インストール対象を `homebrew-tap` だけにします。Webhook は不要です。
2. App の Repository permissions は `Actions: Read and write` と自動付与の `Metadata: Read-only` のみ。Contents、Administration、Secrets、Workflows の権限は不要です。Actions write はワークフロー起動以外の Actions 操作も含むため、名前付きワークフローだけに限定された権限ではありません。
3. 通知元 `mizu-pairrank` に変数 `HOMEBREW_TAP_APP_CLIENT_ID` と secret `HOMEBREW_TAP_APP_PRIVATE_KEY` を登録します。秘密鍵は所有者が GitHub の安全な入力欄から直接登録し、チャット・リポジトリ・ログへ貼り付けないでください。
4. Tap の更新ジョブは `GITHUB_TOKEN` の `contents: write` を使います。リポジトリ全体の既定権限や PR 自動承認設定を広げる必要はありません。
5. Tap と通知元の変更をレビューして main に取り込みます。Tap の [Update verified release casks](https://github.com/mizucopo/homebrew-tap/actions/workflows/update-casks.yml) を `apply=false` で手動実行し、実際の公開 ZIP の検証が成功することを確認します。
6. Tap の変数 `HOMEBREW_AUTO_UPDATE_ENABLED=true` を設定します。必要なら `apply=true` で手動実行し、同一版ではコミットされないことを確認します。
7. 通知元の変数 `HOMEBREW_TAP_NOTIFY_ENABLED=true` を設定します。次回の安定版リリース後、通知ジョブと Tap の実行・コミットを確認します。

App のトークンは通知ジョブで発行し、権限は Tap の Actions write に絞ります。公式 `actions/create-github-app-token` の終了処理で破棄します。App の秘密鍵自体には更新・失効管理が必要です。

設定の確認先:

- [GitHub Apps](https://github.com/settings/apps)
- [App installations](https://github.com/settings/installations)
- [通知元の Actions variables](https://github.com/mizucopo/mizu-pairrank/settings/variables/actions)
- [通知元の Actions secrets](https://github.com/mizucopo/mizu-pairrank/settings/secrets/actions)
- [Tap の Actions variables](https://github.com/mizucopo/homebrew-tap/settings/variables/actions)
- [Tap の実行履歴](https://github.com/mizucopo/homebrew-tap/actions/workflows/update-casks.yml)

## 失敗時・停止時

- 通知だけが失敗した場合: 通知元の失敗ジョブを再実行するか、Tap のワークフローを手動実行します。重複通知は安全です
- Tap の検証失敗: ログの原因を直します。同じ版の SHA が変わった場合、自動承認せず配布元を調べます
- push 拒否: 権限・ルールを確認します。この処理は保護設定を緩めません。必須 PR ルールを新設する場合は公開方式の再設計が必要です
- 一時停止: Tap の `HOMEBREW_AUTO_UPDATE_ENABLED` を `false` にします。通知も止めるなら通知元の `HOMEBREW_TAP_NOTIFY_ENABLED` を `false` にします
- 鍵の失効: 新しい鍵を安全に登録し直し、古い鍵を無効にして動作を確認します

## アプリの追加

1. 手動レビューで `Casks/<token>.rb` を追加し、アセット実物とインストールを検証します。
2. `apps.json` に owner/repository、Cask token、tag prefix (`""` または `"v"`)、`{version}` を含む ZIP 名、`.app` 名、bundle ID を登録します。
3. 新しいアプリの Release 完了後にも同じ Tap ワークフローの通知ジョブを追加します。新しい通知元への秘密鍵登録は、そのリポジトリが App の権限を行使できるようにする変更なので改めて承認・レビューします。
4. テスト・dry run・対応 Mac でのインストールを確認してから、その通知元を有効にします。

Intel/universal、DMG、CLI formula、prerelease、build metadata 付き SemVer は今の自動処理の対象外です。形式を足すときは検証とテストを追加し、ARM64 用のチェックを省略しないでください。

## ローカル検証

```sh
python3 -m unittest discover -s automation/tests -v
bash -n automation/publish.sh
python3 automation/update_casks.py --check
```

`publish.sh` は使い捨て GitHub Actions checkout 専用です。ローカル作業ツリーでは実行しないでください。

Python と shell のテストは Linux でも実行できます。Homebrew の style/audit、実機でのインストール・起動・アップグレードは別途対応 Mac で確認してください。

## 参考

- [Workflow dispatch API](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
- [GITHUB_TOKEN からのワークフロー起動と制限](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow)
- [GitHub App の Actions 認証](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow)
- [Homebrew Cask Cookbook](https://docs.brew.sh/Cask-Cookbook)
