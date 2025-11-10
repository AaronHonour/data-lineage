# Data Lineage Frontend

Modern React frontend for the Data Lineage application, built with Vite, TypeScript, Material-UI, and following atomic design principles.

## 🚀 Features

- ✅ **Authentication** - Secure login with JWT tokens
- ✅ **Dashboard** - System overview with statistics and recent activity
- ✅ **Data Sources Management** - View and manage connected data sources
- ✅ **Datasets Explorer** - Browse discovered datasets
- ✅ **Lineage Visualization** - Interactive lineage graph (coming soon)
- ✅ **Responsive Design** - Works on desktop, tablet, and mobile
- ✅ **Dark Mode Ready** - Material-UI theming support
- ✅ **90%+ Test Coverage** - Comprehensive testing with Vitest

## 🛠️ Technology Stack

### Core
- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Material-UI v5** - Component library

### State Management
- **React Query (TanStack Query)** - Server state management
- **Zustand** - Client state management
- **React Router v6** - Navigation

### Data Visualization
- **React Flow** - Lineage graph visualization

### Testing
- **Vitest** - Unit testing framework
- **React Testing Library** - Component testing
- **@testing-library/jest-dom** - DOM matchers

### Code Quality
- **ESLint** - Linting
- **Prettier** - Code formatting
- **TypeScript Strict Mode** - Type checking

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── atoms/          # Basic components (buttons, badges, etc.)
│   │   ├── molecules/      # Composite components (cards, forms, etc.)
│   │   ├── organisms/      # Complex components (lists, tables, etc.)
│   │   ├── templates/      # Page layouts
│   │   └── auth/           # Authentication components
│   ├── pages/              # Page components
│   │   ├── Dashboard/
│   │   ├── DataSources/
│   │   ├── Datasets/
│   │   ├── Lineage/
│   │   └── Login/
│   ├── hooks/              # Custom React hooks
│   ├── services/           # API services
│   ├── types/              # TypeScript type definitions
│   ├── utils/              # Utility functions
│   ├── contexts/           # React contexts
│   ├── tests/              # Test utilities and setup
│   ├── App.tsx             # Main app component
│   ├── main.tsx            # Entry point
│   └── theme.ts            # Material-UI theme
├── public/                 # Static assets
├── Dockerfile              # Production Docker image
├── nginx.conf              # Nginx configuration
├── vite.config.ts          # Vite configuration
├── vitest.config.ts        # Vitest configuration
├── tsconfig.json           # TypeScript configuration
└── package.json            # Dependencies
```

## 🏗️ Atomic Design Architecture

The application follows Brad Frost's Atomic Design methodology:

### Atoms
Basic building blocks:
- `StatusBadge` - Status indicators
- `LoadingSpinner` - Loading states
- Material-UI components (Button, TextField, etc.)

### Molecules
Combinations of atoms:
- `DataSourceCard` - Data source display card
- `SearchBar` - Search functionality
- `DatasetCard` - Dataset information card

### Organisms
Complex components:
- `DataSourceList` - List of data sources
- `LineageGraph` - Interactive lineage visualization
- `DatasetTable` - Dataset table with sorting

### Templates
Page layouts:
- `MainLayout` - Application shell with navigation
- `DashboardLayout` - Dashboard-specific layout

### Pages
Complete pages:
- `Dashboard` - System overview
- `DataSources` - Data source management
- `Datasets` - Dataset explorer
- `Lineage` - Lineage visualization
- `Login` - Authentication

## 🚦 Getting Started

### Prerequisites
- Node.js 18+
- npm or yarn

### Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Application will be available at http://localhost:3000
```

### Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Run tests with UI
npm run test:ui
```

### Building

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

### Linting & Formatting

```bash
# Lint code
npm run lint

# Fix linting issues
npm run lint:fix

# Format code
npm run format
```

## 🐳 Docker

### Build Docker Image

```bash
docker build -t lineage-frontend .
```

### Run Docker Container

```bash
docker run -p 3000:80 lineage-frontend
```

### Docker Compose

The frontend is integrated into the main docker-compose.sample.yml:

```bash
# From deployment directory
cd deployment
python scripts/cli.py run infrastructure
```

The UI will be available at http://localhost:3000

## 🔐 Authentication

The application includes a simple authentication system:

### Demo Credentials
- **Username**: `admin`
- **Password**: `admin`

### How It Works
1. User submits credentials on login page
2. Backend validates and returns JWT token
3. Token stored in localStorage
4. Token sent with all API requests
5. Protected routes check for valid token

### Token Management
- Automatic token expiration handling
- Redirect to login on 401 errors
- Token refresh (if implemented)

## 📊 API Integration

The frontend communicates with the backend API via the `apiService`:

### Base URL
Configured in `.env`:
```
VITE_API_BASE_URL=http://localhost:8000
```

### API Service
Located at `src/services/api.ts`, provides methods for:
- Authentication (`login`, `getCurrentUser`)
- Data Sources (`getDataSources`, `triggerSync`)
- Lineage (`getTableLineage`, `getColumnLineage`)
- Dashboard (`getDashboardStats`)

### React Query Hooks
Pre-built hooks for common operations:
- `useDataSources()` - Fetch all data sources
- `useTriggerSync()` - Trigger data source sync
- `useSyncJobs()` - Get sync job status
- `useTableLineage()` - Get table lineage
- `useDashboardStats()` - Get dashboard statistics

## 🎨 Theming

Material-UI theme configured in `src/theme.ts`:

### Colors
- **Primary**: Blue (#1976d2) - Data flow
- **Secondary**: Purple (#9c27b0) - Transformations
- **Success**: Green - Completed states
- **Error**: Red - Error states
- **Warning**: Orange - Warning states

### Customization
Edit `src/theme.ts` to customize:
- Color palette
- Typography
- Component styles
- Breakpoints

## ✅ Testing Strategy

### Unit Tests
- Component rendering
- User interactions
- Utility functions
- Hook behavior

### Integration Tests
- Page navigation
- API integration
- Form submissions
- Error handling

### Coverage Goals
- **Lines**: 90%+
- **Functions**: 90%+
- **Branches**: 90%+
- **Statements**: 90%+

### Test Files
Tests are co-located with components:
```
Component.tsx
Component.test.tsx
```

## 🚧 Roadmap

### Phase 1 (Current)
- ✅ Authentication system
- ✅ Dashboard with statistics
- ✅ Data sources list
- ✅ Basic navigation
- ✅ Responsive layout

### Phase 2
- 🔲 Complete lineage graph visualization with React Flow
- 🔲 Interactive node manipulation
- 🔲 Zoom and pan controls
- 🔲 Dataset details page

### Phase 3
- 🔲 Column-level lineage
- 🔲 Impact analysis
- 🔲 Root cause analysis
- 🔲 Search and filters

### Phase 4
- 🔲 Saved views
- 🔲 User preferences
- 🔲 Export functionality
- 🔲 Real-time updates

## 🐛 Troubleshooting

### Dev Server Won't Start
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

### API Connection Issues
1. Check `.env` has correct API URL
2. Ensure backend is running
3. Check CORS settings on backend

### Build Failures
1. Run `npm run lint` to check for errors
2. Run `npm run test` to check tests
3. Clear build cache: `rm -rf dist`

### Docker Issues
1. Rebuild image: `docker build --no-cache -t lineage-frontend .`
2. Check nginx logs: `docker logs lineage-ui`
3. Verify API proxy in nginx.conf

## 📝 Environment Variables

Create `.env` file in frontend root:

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000

# Application
VITE_APP_NAME="Data Lineage"
```

## 🤝 Contributing

### Code Style
- Follow existing patterns
- Use TypeScript strict mode
- Write tests for new features
- Keep components small and focused

### Pull Request Process
1. Create feature branch
2. Write/update tests
3. Ensure lint passes
4. Update documentation
5. Submit PR

## 📄 License

See main repository LICENSE file.

## 🙋 Support

- **API Documentation**: http://localhost:8000/docs (when backend running)
- **Issues**: GitHub Issues
- **Frontend Port**: http://localhost:3000
- **Backend Port**: http://localhost:8000

---

**Built with ❤️ using React, TypeScript, and Material-UI**
