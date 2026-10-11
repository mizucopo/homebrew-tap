cask "mizu-pairrank" do
  version "1.5.1"
  sha256 "42b924b88e4fc70a9877a114bd6d01de980704d1022d9c8cc99f8aa2e139029d"

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
