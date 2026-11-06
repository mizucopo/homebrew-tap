cask "mizu-pairrank" do
  version "1.8.0"
  sha256 "ce9abb1f62a92008539d2be64eccddc912bd53c3bfe9438d5f9fbe0f70067dd5"

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
