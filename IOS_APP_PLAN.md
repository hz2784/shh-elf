# SHH-ELF iOS App - Development Plan

## Project Overview

**App Name:** SHH-ELF iOS
**Platform:** iOS 16.0+
**Language:** Swift
**UI Framework:** SwiftUI
**Primary Feature:** Camera-based bookshelf scanning and AI-powered book recommendations

## Architecture

### Tech Stack

- **Language:** Swift 5.9+
- **UI:** SwiftUI
- **Camera:** AVFoundation
- **Image Processing:** Vision framework (OCR)
- **Networking:** URLSession / Alamofire
- **Audio Playback:** AVPlayer
- **Image Handling:** UIKit (for camera) + SwiftUI integration

### Project Structure

```
ShhElfIOS/
├── ShhElfIOS/
│   ├── App/
│   │   ├── ShhElfIOSApp.swift          # App entry point
│   │   └── AppDelegate.swift           # Lifecycle management
│   ├── Models/
│   │   ├── BookModel.swift             # Book data model
│   │   ├── ShelfAnalysisResponse.swift # API response model
│   │   └── RecommendationModel.swift   # Recommendation data
│   ├── Views/
│   │   ├── HomeView.swift              # Main landing screen
│   │   ├── CameraView.swift            # Camera capture UI
│   │   ├── BookshelfScannerView.swift  # Camera viewfinder
│   │   ├── AnalysisResultView.swift    # Show detected books
│   │   ├── RecommendationListView.swift # Book recommendations
│   │   └── BookDetailView.swift        # Individual book details
│   ├── ViewModels/
│   │   ├── CameraViewModel.swift       # Camera logic
│   │   ├── AnalysisViewModel.swift     # API integration
│   │   └── AudioPlayerViewModel.swift  # Audio playback
│   ├── Services/
│   │   ├── APIService.swift            # API client
│   │   ├── CameraService.swift         # Camera capture
│   │   ├── ImageProcessor.swift        # Image enhancement
│   │   └── AudioService.swift          # Audio playback
│   ├── Utilities/
│   │   ├── Constants.swift             # App constants
│   │   ├── Extensions.swift            # Swift extensions
│   │   └── NetworkMonitor.swift        # Network status
│   └── Resources/
│       ├── Assets.xcassets             # Images, colors
│       └── Info.plist                  # App configuration
└── Tests/
    ├── ShhElfIOSTests/
    └── ShhElfIOSUITests/
```

## Core Features

### 1. Camera Capture
- **Framework:** AVFoundation
- **Features:**
  - Real-time camera preview
  - Tap to capture photo
  - Photo library access (optional)
  - Image quality optimization
  - Flash control
  - Focus/exposure adjustment

### 2. Image Processing
- **Pre-processing:**
  - Resize for optimal API upload
  - Compression (JPEG, 80-90% quality)
  - Orientation correction
  - Contrast/brightness enhancement

- **Post-capture:**
  - Preview captured image
  - Retake option
  - Crop/adjust (optional v2 feature)

### 3. API Integration

#### Endpoint: POST /api/analyze-bookshelf
**Request:**
```swift
// Multipart form data
Content-Type: multipart/form-data
Authorization: Bearer <token> (optional)

file: <image_data>
```

**Response Model:**
```swift
struct ShelfAnalysisResponse: Codable {
    let success: Bool
    let detectedBooks: [DetectedBook]
    let readingPreferences: ReadingPreferences
    let recommendedBooks: [RecommendedBook]
    let analysisSummary: String
    let confidenceScore: Double
    let analysisId: String
}

struct DetectedBook: Codable {
    let title: String
    let author: String
    let genre: String
    let confidence: Double
}

struct ReadingPreferences: Codable {
    let favoriteGenres: [String]
    let readingLevel: String
    let interests: [String]
    let authorPreferences: String
}

struct RecommendedBook: Codable {
    let title: String
    let author: String
    let reason: String
    let matchScore: Double
}
```

### 4. Audio Playback
- Stream audio URLs from API responses
- Play/pause controls
- Progress indicator
- Background playback support (optional)

### 5. User Interface Flow

```
Launch Screen
    ↓
Home View
    ├── "Scan Bookshelf" Button
    ├── Recent Scans (v2)
    └── Settings (v2)
    ↓
Camera View
    ├── Viewfinder
    ├── Capture Button
    ├── Flash Toggle
    └── Cancel Button
    ↓
Image Preview
    ├── Retake Button
    └── Analyze Button
    ↓
Loading View
    └── "Analyzing your bookshelf..."
    ↓
Analysis Results View
    ├── Detected Books List
    ├── Reading Preferences Summary
    ├── Confidence Score
    └── "View Recommendations" Button
    ↓
Recommendations View
    ├── Recommended Books List
    ├── Match Scores
    └── Book Detail Tap
    ↓
Book Detail View
    ├── Title, Author
    ├── Recommendation Reason
    ├── Audio Player (if available)
    └── Actions (share, save, etc.)
```

## API Configuration

### Base URL
```swift
// Constants.swift
struct APIConstants {
    static let baseURL = "https://shh-elf.onrender.com"
    static let analyzeBookshelfEndpoint = "/api/analyze-bookshelf"
    static let healthEndpoint = "/api/health"
}
```

### Network Layer
```swift
class APIService {
    static let shared = APIService()

    func analyzeBookshelf(image: UIImage) async throws -> ShelfAnalysisResponse {
        // 1. Convert UIImage to JPEG data
        // 2. Create multipart form data
        // 3. Upload to API
        // 4. Parse response
        // 5. Return ShelfAnalysisResponse
    }
}
```

## Camera Implementation Plan

### Step 1: Request Permissions
```swift
// Info.plist entries required:
NSCameraUsageDescription: "SHH-ELF needs camera access to scan your bookshelf"
NSPhotoLibraryUsageDescription: "SHH-ELF needs photo access to select bookshelf images"
```

### Step 2: Camera Service
```swift
class CameraService: NSObject, ObservableObject {
    @Published var capturedImage: UIImage?
    @Published var isAuthorized = false

    private let session = AVCaptureSession()
    private let output = AVCapturePhotoOutput()

    func checkPermissions()
    func setupCamera()
    func capturePhoto()
}
```

### Step 3: SwiftUI Camera View
```swift
struct CameraView: View {
    @StateObject private var cameraService = CameraService()

    var body: some View {
        ZStack {
            CameraPreview(session: cameraService.session)

            VStack {
                Spacer()

                // Capture button
                Button(action: { cameraService.capturePhoto() }) {
                    Circle()
                        .fill(Color.white)
                        .frame(width: 70, height: 70)
                }
            }
        }
    }
}
```

## Image Processing Strategy

### Pre-Upload Enhancement
1. **Resize:** Max dimension 1200px (matching backend expectations)
2. **Format:** JPEG with 85-90% quality
3. **Orientation:** Auto-correct based on EXIF
4. **Enhancement:**
   - Increase contrast by 20%
   - Increase sharpness by 30%
   - Increase brightness by 10%
   - (Matches backend `process_uploaded_image` function)

### Code Example
```swift
class ImageProcessor {
    static func prepareForUpload(_ image: UIImage) -> Data? {
        // 1. Resize to max 1200px
        let resized = image.resized(maxDimension: 1200)

        // 2. Enhance (optional, backend also does this)
        let enhanced = resized.enhanced()

        // 3. Convert to JPEG
        return enhanced.jpegData(compressionQuality: 0.85)
    }
}
```

## MVP Feature Set

### Version 1.0 (MVP)
- ✅ Camera capture
- ✅ Photo upload to API
- ✅ Display detected books
- ✅ Show reading preferences
- ✅ List recommended books
- ✅ Basic error handling
- ✅ Loading states

### Version 1.1 (Enhancement)
- Audio playback for recommendations
- Photo library selection
- Scan history (local storage)
- Share results
- Dark/light mode
- Localization (English/Chinese)

### Version 2.0 (Advanced)
- User authentication
- Save scans to cloud
- Multiple bookshelf profiles
- AR overlay (book spine highlighting)
- Manual book entry
- Export to PDF/share

## Development Phases

### Phase 1: Project Setup (Week 1)
- Create Xcode project
- Setup project structure
- Configure Info.plist permissions
- Add basic navigation

### Phase 2: Camera Implementation (Week 1-2)
- Implement AVFoundation camera
- Create SwiftUI camera view
- Add image capture
- Test on device

### Phase 3: API Integration (Week 2)
- Build API service layer
- Create data models
- Implement multipart upload
- Test with backend

### Phase 4: UI/UX (Week 3)
- Design results screen
- Build recommendations list
- Add loading states
- Polish UI

### Phase 5: Testing & Polish (Week 4)
- End-to-end testing
- Error handling
- Performance optimization
- App Store preparation

## Key iOS Frameworks

```swift
import SwiftUI           // UI framework
import AVFoundation      // Camera capture
import UIKit            // Image handling
import Combine          // Reactive programming
import PhotosUI         // Photo picker
```

## Privacy & Permissions

### Required Permissions
1. **Camera Access** - Primary feature
2. **Photo Library** - Optional alternate input

### Privacy Considerations
- Images processed server-side (inform users)
- No local storage of sensitive data (MVP)
- HTTPS only for API calls
- Optional user authentication

## Testing Strategy

### Unit Tests
- API service tests
- Image processing tests
- Model parsing tests

### UI Tests
- Camera flow
- Upload flow
- Results display
- Error scenarios

### Manual Testing
- Test with various bookshelves
- Test lighting conditions
- Test different book arrangements
- Test error states (no network, etc.)

## Deployment

### App Store Requirements
- App name: SHH-ELF
- Category: Education / Books
- Target: iOS 16.0+
- Privacy policy required
- Screenshots (6.7", 6.5", 5.5" displays)
- App icon (1024x1024)

### Configuration
```swift
// Build settings
PRODUCT_BUNDLE_IDENTIFIER = com.shhelf.ios
MARKETING_VERSION = 1.0
CURRENT_PROJECT_VERSION = 1
TARGETED_DEVICE_FAMILY = 1 (iPhone only for MVP)
```

## Next Steps

1. **Create new GitHub repo:** `shh-elf-ios`
2. **Initialize Xcode project:**
   - App name: SHH-ELF
   - Organization: Your org name
   - Bundle ID: com.shhelf.ios
   - Interface: SwiftUI
   - Life Cycle: SwiftUI App
   - Language: Swift

3. **Install dependencies (if needed):**
   - Consider Alamofire for networking (optional)
   - Consider Kingfisher for image caching (v2)

4. **Start with Phase 1:** Project structure and camera permissions

## Backend API Notes

Your existing backend at `https://shh-elf.onrender.com` already supports:
- ✅ Image upload via `/api/analyze-bookshelf`
- ✅ GPT-4o Vision for book detection
- ✅ OCR preprocessing with pytesseract
- ✅ Image enhancement (contrast, sharpness, brightness)
- ✅ JSON response with books, preferences, recommendations

**No backend changes needed for iOS MVP!** 🎉

## Estimated Timeline

- **MVP (v1.0):** 3-4 weeks
- **Enhanced (v1.1):** +2 weeks
- **Advanced (v2.0):** +4 weeks

---

## Quick Start Checklist

- [ ] Create GitHub repo `shh-elf-ios`
- [ ] Create new Xcode project
- [ ] Add camera permission to Info.plist
- [ ] Create project folder structure
- [ ] Implement camera service
- [ ] Build API client
- [ ] Test with backend API
- [ ] Design UI screens
- [ ] Add error handling
- [ ] Test on physical device
- [ ] Submit to App Store

---

**Ready to start coding?** Begin with creating the Xcode project and implementing the camera service!
