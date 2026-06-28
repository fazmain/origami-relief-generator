import fs from "fs";
import path from "path";

export default async function globalSetup() {
  const fixtureDir = path.join(__dirname, "fixtures");
  fs.mkdirSync(fixtureDir, { recursive: true });

  const imgPath = path.join(fixtureDir, "test-image.png");
  if (!fs.existsSync(imgPath)) {
    // Fixture missing — regenerate with:
    //   cd backend && source venv/bin/activate
    //   python3 -c "import cv2, numpy as np; cv2.imwrite('../frontend/tests/e2e/fixtures/test-image.png', np.ones((50,50,3),dtype='uint8')*180)"
    throw new Error(
      `Test fixture missing: ${imgPath}\nRun the command in the comment above to regenerate it.`
    );
  }
}
