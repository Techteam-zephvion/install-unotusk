import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:app/models/models.dart';
import 'package:app/theme/app_theme.dart';
import 'package:app/widgets/sidebar.dart';

void main() {
  testWidgets('UnoSidebar collapsed layout is centered and not shifted left',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Row(
            children: [
              UnoSidebar(
                open: false,
                onToggle: () {},
                onNewQuery: () {},
                palette: UnoPalette.light,
                activeView: 'chat',
                onViewChange: (_) {},
                onLoadRecentChat: (_) {},
                user: const UserModel(name: 'Naren D', org: 'Acme Corp'),
                onLogOut: () {},
                onNavigateSettings: (_) {},
                onOpenArchivedModal: () {},
              ),
              const Expanded(child: SizedBox()),
            ],
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify sidebar width is 72.0
    final sidebarFinder = find.byType(UnoSidebar);
    expect(sidebarFinder, findsOneWidget);
    final sidebarSize = tester.getSize(sidebarFinder);
    expect(sidebarSize.width, 72.0);

    // Verify Expand Chevron button is horizontally centered (width: 36, offset dx: 18.0)
    final chevronFinder = find.byIcon(LucideIcons.chevronRight);
    expect(chevronFinder, findsOneWidget);
    final chevronTopLeft = tester.getTopLeft(chevronFinder);
    // The icon is centered inside the 36px button, so its x position should be near (72 - iconSize)/2 = (72 - 14)/2 = 29.0
    expect(chevronTopLeft.dx, greaterThan(20.0));
    expect(chevronTopLeft.dx, lessThan(40.0));

    // Verify New Query Plus button icon is centered
    final plusFinder = find.byIcon(LucideIcons.plus);
    expect(plusFinder, findsOneWidget);
    final plusTopLeft = tester.getTopLeft(plusFinder);
    expect(plusTopLeft.dx, greaterThan(20.0));
    expect(plusTopLeft.dx, lessThan(40.0));

    // Verify Ask (zap) is removed and first nav item (folder) is centered
    expect(find.byIcon(LucideIcons.zap), findsNothing);
    final clipFinder = find.byIcon(LucideIcons.folder);
    expect(clipFinder, findsOneWidget);
    final clipTopLeft = tester.getTopLeft(clipFinder);
    expect(clipTopLeft.dx, greaterThan(20.0));
    expect(clipTopLeft.dx, lessThan(40.0));

    // Verify archive button icon is centered
    final archiveFinder = find.byIcon(LucideIcons.archive);
    expect(archiveFinder, findsOneWidget);
    final archiveTopLeft = tester.getTopLeft(archiveFinder);
    expect(archiveTopLeft.dx, greaterThan(20.0));
    expect(archiveTopLeft.dx, lessThan(40.0));
  });

  testWidgets('UnoSidebar toggling collapse does not throw RenderFlex overflow',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    bool open = true;

    await tester.pumpWidget(
      StatefulBuilder(
        builder: (context, setState) {
          return MaterialApp(
            home: Scaffold(
              body: Row(
                children: [
                  UnoSidebar(
                    open: open,
                    onToggle: () => setState(() => open = !open),
                    onNewQuery: () {},
                    palette: UnoPalette.light,
                    activeView: 'chat',
                    onViewChange: (_) {},
                    onLoadRecentChat: (_) {},
                    user: const UserModel(name: 'Naren D', org: 'Acme Corp'),
                    onLogOut: () {},
                    onNavigateSettings: (_) {},
                    onOpenArchivedModal: () {},
                  ),
                  const Expanded(child: SizedBox()),
                ],
              ),
            ),
          );
        },
      ),
    );

    await tester.pumpAndSettle();

    // Tap collapse button
    await tester.tap(find.byIcon(LucideIcons.panelLeftClose));
    // Pump frames during collapse animation
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
  });

  testWidgets(
      'UnoSidebar excludes Discoveries/Knowledge/Spec History, aligns all nav icons identically, and opens profile menu',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Row(
            children: [
              UnoSidebar(
                open: true,
                onToggle: () {},
                onNewQuery: () {},
                palette: UnoPalette.light,
                activeView: 'chat',
                onViewChange: (_) {},
                onLoadRecentChat: (_) {},
                user: const UserModel(name: 'Dev Lead', org: 'Acme Corporation'),
                onLogOut: () {},
                onNavigateSettings: (_) {},
                onOpenArchivedModal: () {},
              ),
              const Expanded(child: SizedBox()),
            ],
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Removed nav items are not displayed
    expect(find.text('Discoveries'), findsNothing);
    expect(find.text('Knowledge'), findsNothing);
    expect(find.text('Spec History'), findsNothing);

    // Remaining nav items are displayed
    for (final label in [
      'Projects',
      'Overview',
      'Ask AI',
      'Files',
      'Architecture',
      'Ontology Graph',
      'Ingestion Feed',
      'Archived chats',
    ]) {
      expect(find.text(label), findsOneWidget);
    }

    // Active ('Ask AI') and inactive ('Projects', 'Overview', 'Files', 'Archived chats')
    // icons all align to the exact same X coordinate
    final projectsX = tester.getCenter(find.byIcon(LucideIcons.folder)).dx;
    final overviewX =
        tester.getCenter(find.byIcon(LucideIcons.layoutDashboard)).dx;
    final askAiX = tester.getCenter(find.byIcon(LucideIcons.sparkles)).dx;
    final filesX = tester.getCenter(find.byIcon(LucideIcons.folderTree)).dx;
    final archivedX = tester.getCenter(find.byIcon(LucideIcons.archive)).dx;

    expect(overviewX, closeTo(projectsX, 0.5));
    expect(askAiX, closeTo(projectsX, 0.5));
    expect(filesX, closeTo(projectsX, 0.5));
    expect(archivedX, closeTo(projectsX, 0.5));

    // Profile card displays monogram initials and opens popup smoothly on tap
    expect(find.text('DL'), findsOneWidget);
    expect(find.text('Dev Lead'), findsOneWidget);
    expect(find.text('Acme Corporation'), findsOneWidget);

    await tester.tap(find.text('Dev Lead'));
    await tester.pumpAndSettle();

    expect(find.text('Personalization'), findsOneWidget);
    expect(find.text('Sign out'), findsOneWidget);
  });
}
