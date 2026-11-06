cask "mizu-pairrank" do
  version "1.7.0"
  sha256 "6660d4e672aae6d7ac2c2ce0fe45e46c2fd663f478325215e7e0d0221922c044"

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
