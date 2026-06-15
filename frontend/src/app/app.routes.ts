import { Routes } from '@angular/router';
import { ShellComponent } from '@layout/shell/shell.component';
import { authGuard, mainGuard } from '@core/guards';

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [mainGuard],
    loadComponent: () =>
      import('./features/auth/login/login.component').then(m => m.LoginComponent),
  },
  {
    path: 'forgot-password',
    canActivate: [mainGuard],
    loadComponent: () =>
      import('./features/auth/forget-password/forget-password.component').then(
        c => c.ForgetPasswordComponent
      ),
  },
  {
    path: 'register',
    canActivate: [mainGuard],
    loadComponent: () =>
      import('./features/auth/signup/signup.component').then(
        c => c.SignupComponent
      ),
  },
  {
    path: 'reset-password',
    canActivate: [mainGuard],
    loadComponent: () =>
      import('./features/auth/forget-password/forget-password.component').then(
        c => c.ForgetPasswordComponent
      ),
  },
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    canActivateChild: [authGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },

      // Dashboard
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
      },

      // Incidents
      {
        path: 'incidents',
        loadComponent: () =>
          import('./features/incidents/incident-list/incident-list.component').then(m => m.IncidentListComponent),
      },
      {
        path: 'incidents/:id',
        loadComponent: () =>
          import('./features/incidents/incident-detail/incident-detail.component').then(m => m.IncidentDetailComponent),
      },

      // Cameras
      {
        path: 'cameras',
        loadComponent: () =>
          import('./features/cameras/camera-list/camera-list.component').then(m => m.CameraListComponent),
      },
      {
        path: 'cameras/new',
        loadComponent: () =>
          import('./features/cameras/camera-list/camera-list.component').then(m => m.CameraListComponent),
      },
      {
        path: 'cameras/:id',
        loadComponent: () =>
          import('./features/cameras/camera-list/camera-list.component').then(m => m.CameraListComponent),
      },
      {
        path: 'cameras/:id/edit',
        loadComponent: () =>
          import('./features/cameras/camera-list/camera-list.component').then(m => m.CameraListComponent),
      },

      // Edge Nodes
      {
        path: 'edge-nodes',
        loadComponent: () =>
          import('./features/edge-nodes/edge-node-list/edge-node-list.component').then(m => m.EdgeNodeListComponent),
      },
      {
        path: 'edge-nodes/:id',
        loadComponent: () =>
          import('./features/edge-nodes/edge-node-list/edge-node-list.component').then(m => m.EdgeNodeListComponent),
      },

      // Analytics (tabbed with child routes)
      {
        path: 'analytics',
        loadComponent: () =>
          import('./features/analytics/analytics.component').then(m => m.AnalyticsComponent),
        children: [
          { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
          { path: 'dashboard', loadComponent: () => import('./features/analytics/analytics.component').then(m => m.AnalyticsComponent) },
          { path: 'motion-chaos', loadComponent: () => import('./features/analytics/analytics.component').then(m => m.AnalyticsComponent) },
          { path: 'audio-triggers', loadComponent: () => import('./features/analytics/analytics.component').then(m => m.AnalyticsComponent) },
          { path: 'vlm-performance', loadComponent: () => import('./features/analytics/analytics.component').then(m => m.AnalyticsComponent) },
          { path: 'incidents', loadComponent: () => import('./features/analytics/analytics.component').then(m => m.AnalyticsComponent) },
          { path: 'heatmap', loadComponent: () => import('./features/analytics/analytics.component').then(m => m.AnalyticsComponent) },
          { path: 'response-times', loadComponent: () => import('./features/analytics/analytics.component').then(m => m.AnalyticsComponent) },
          { path: 'reports', loadComponent: () => import('./features/analytics/analytics.component').then(m => m.AnalyticsComponent) },
        ],
      },

      // Alerts
      {
        path: 'alerts',
        loadComponent: () =>
          import('./features/alerts/alert-list/alert-list.component').then(m => m.AlertListComponent),
      },
      {
        path: 'alerts/preferences',
        loadComponent: () =>
          import('./features/alerts/alert-list/alert-list.component').then(m => m.AlertListComponent),
      },

      // ML Models
      {
        path: 'ml-models',
        loadComponent: () =>
          import('./features/ml-models/model-list/model-list.component').then(m => m.ModelListComponent),
      },
      {
        path: 'ml-models/fusion-weights',
        loadComponent: () =>
          import('./features/ml-models/model-list/model-list.component').then(m => m.ModelListComponent),
      },
      {
        path: 'ml-models/:id',
        loadComponent: () =>
          import('./features/ml-models/model-list/model-list.component').then(m => m.ModelListComponent),
      },

      // Training
      {
        path: 'training',
        loadComponent: () =>
          import('./features/training/training-list/training-list.component').then(m => m.TrainingListComponent),
      },
      {
        path: 'training/new',
        loadComponent: () =>
          import('./features/training/training-list/training-list.component').then(m => m.TrainingListComponent),
      },
      {
        path: 'training/:id',
        loadComponent: () =>
          import('./features/training/training-list/training-list.component').then(m => m.TrainingListComponent),
      },

      // Datasets
      {
        path: 'datasets',
        loadComponent: () =>
          import('./features/datasets/dataset-list/dataset-list.component').then(m => m.DatasetListComponent),
      },
      {
        path: 'datasets/:id',
        loadComponent: () =>
          import('./features/datasets/dataset-list/dataset-list.component').then(m => m.DatasetListComponent),
      },

      // Annotations
      {
        path: 'annotations',
        loadComponent: () =>
          import('./features/annotations/annotation-list/annotation-list.component').then(m => m.AnnotationListComponent),
      },
      {
        path: 'annotations/:id',
        loadComponent: () =>
          import('./features/annotations/annotation-list/annotation-list.component').then(m => m.AnnotationListComponent),
      },

      // Zones
      {
        path: 'zones',
        loadComponent: () =>
          import('./features/zones/zone-list/zone-list.component').then(m => m.ZoneListComponent),
      },
      {
        path: 'zones/new',
        loadComponent: () =>
          import('./features/zones/zone-list/zone-list.component').then(m => m.ZoneListComponent),
      },
      {
        path: 'zones/:id',
        loadComponent: () =>
          import('./features/zones/zone-list/zone-list.component').then(m => m.ZoneListComponent),
      },
      {
        path: 'zones/:id/edit',
        loadComponent: () =>
          import('./features/zones/zone-list/zone-list.component').then(m => m.ZoneListComponent),
      },

      // Chatbot
      {
        path: 'chatbot',
        loadComponent: () =>
          import('./features/chatbot/chatbot.component').then(m => m.ChatbotComponent),
      },

      // Users (admin only — guard enforced at component level)
      {
        path: 'users',
        loadComponent: () =>
          import('./features/users/user-list/user-list.component').then(m => m.UserListComponent),
      },
      {
        path: 'users/new',
        loadComponent: () =>
          import('./features/users/user-list/user-list.component').then(m => m.UserListComponent),
      },
      {
        path: 'users/:id',
        loadComponent: () =>
          import('./features/users/user-list/user-list.component').then(m => m.UserListComponent),
      },
      {
        path: 'users/:id/edit',
        loadComponent: () =>
          import('./features/users/user-list/user-list.component').then(m => m.UserListComponent),
      },

      // Settings
      {
        path: 'settings',
        loadComponent: () =>
          import('./features/settings/settings.component').then(m => m.SettingsComponent),
      },
      {
        path: 'settings/general',
        loadComponent: () =>
          import('./features/settings/settings.component').then(m => m.SettingsComponent),
      },
      {
        path: 'settings/audit-logs',
        loadComponent: () =>
          import('./features/settings/settings.component').then(m => m.SettingsComponent),
      },
      {
        path: 'settings/api-keys',
        loadComponent: () =>
          import('./features/settings/settings.component').then(m => m.SettingsComponent),
      },
      {
        path: 'settings/security',
        loadComponent: () =>
          import('./features/settings/settings.component').then(m => m.SettingsComponent),
      },

      // Notifications
      {
        path: 'notifications',
        loadComponent: () =>
          import('./features/notifications/notifications.component').then(m => m.NotificationsComponent),
      },
    ],
  },
  { path: '**', redirectTo: 'dashboard' },
];
