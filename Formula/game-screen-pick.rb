class GameScreenPick < Formula
  desc "Select full-resolution screenshots from game recordings"
  homepage "https://github.com/mizucopo/game-screen-pick"
  license all_of: ["MIT", "OFL-1.1"]

  if OS.mac?
    url "https://github.com/mizucopo/game-screen-pick/releases/download/2.0.1/game-screen-pick-2.0.1-macos-arm64.tar.gz"
    sha256 "de6d80217641d41cd52ff8c4679b6287f7c69cf71ef97b20f3466edb65d970d0"
  else
    url "https://github.com/mizucopo/game-screen-pick/releases/download/2.0.1/game-screen-pick-2.0.1-linux-x86_64.tar.gz"
    sha256 "0dedf9778932147df7d385c4fbc0836eb828de6a41dcc583df88507b850f1607"
  end

  livecheck do
    url :stable
    strategy :github_latest
  end

  depends_on "ffmpeg"

  on_macos do
    depends_on arch: :arm64
    depends_on macos: :sonoma
  end

  on_linux do
    depends_on arch: :x86_64
  end

  def install
    bin.install "game-screen-pick"
    pkgshare.install "config.example.toml"
    doc.install "README.md", "docs", "BUILD-INFO.json", "DEPENDENCIES.txt"
    prefix.install "licenses"
  end

  test do
    assert_match "game-screen-pick #{version}", shell_output("#{bin}/game-screen-pick --version")
    system formula_opt_bin("ffmpeg")/"ffmpeg", "-f", "lavfi", "-i", "testsrc=size=64x64:rate=2",
           "-t", "1", "-c:v", "ffv1", "input.mkv"
    system bin/"game-screen-pick", "extract", "--at", "0.5", "input.mkv", "frames"
    assert_path_exists testpath/"frames/frame.png"
    assert_path_exists testpath/"frames/extraction.json"
  end
end
