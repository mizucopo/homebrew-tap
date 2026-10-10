cask "mizu-pairrank" do
  version "1.1.0"
  sha256 "317c9e5a988300a78e08ccc64971bc6545f8b2b76c23c68069ef511d580090e4"

  url "https://github.com/mizucopo/mizu-pairrank/releases/download/#{version}/mizu-pairrank-#{version}-macos-arm64.zip"
  name "mizu-pairrank"
  desc "Build personal rankings through pairwise comparisons"
  homepage "https://github.com/mizucopo/mizu-pairrank"

  livecheck do
    url :url
    strategy :github_latest
  end

  depends_on arch: :arm64
  depends_on :macos

  app "mizu-pairrank.app"

  caveats <<~EOS
    This macOS release is ad-hoc signed and is not notarized.
    macOS Gatekeeper may prevent it from opening after installation.
  EOS
end
