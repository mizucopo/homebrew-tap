cask "mizu-pairrank" do
  version "1.6.2"
  sha256 "4a53c9d2fff678b7d9645b704194beba4f5726f4c063e4e95998ec7b4884dd3f"

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
