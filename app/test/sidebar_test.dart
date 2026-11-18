import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:app/models/models.dart';
import 'package:app/theme/app_theme.dart';
import 'package:app/widgets/sidebar.dart';
import 'package:app/widgets/unotusk_logo.dart';

void main() {
  testWidgets(
      'UnoSidebar collapsed layout is centered, logo morphs to open button on hover, and tooltips render to the right',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    bool toggled = false;

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Row(
            children: [
              UnoSidebar(
                open: false,
                onToggle: () => toggled = true,
                onNewQuery: () {},
                palette: UnoPalette.dark,
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
    expect(tester.getSize(sidebarFinder).width, 72.0);

    // No separate expand chevron button — logo handles expand on hover
    expect(find.byIcon(LucideIcons.chevronRight), findsNothing);

    // Verify Logo, New Query Plus, Projects folder, and Archive icons are all centered at x = 36.0
    final logoFinder = find.byType(UnotuskLogo);
    final plusFinder = find.byIcon(LucideIcons.plus);
    final folderFinder = find.byIcon(LucideIcons.folder);
    final archiveFinder = find.byIcon(LucideIcons.archive);

    expect(logoFinder, findsOneWidget);
    expect(plusFinder, findsOneWidget);
    expect(folderFinder, findsOneWidget);
    expect(archiveFinder, findsOneWidget);

    expect(tester.getCenter(logoFinder).dx, closeTo(36.0, 1.0));
    expect(tester.getCenter(plusFinder).dx, closeTo(36.0, 1.0));
    expect(tester.getCenter(folderFinder).dx, closeTo(36.0, 1.0));
    expect(tester.getCenter(archiveFinder).dx, closeTo(36.0, 1.0));

    // Hover over the collapsed Unotusk logo -> morphs into panelLeftOpen & shows right-side "Open sidebar" pill
    final gesture = await tester.createGesture(kind: PointerDeviceKind.mouse);
    await gesture.addPointer(location: Offset.zero);
    addTearDown(gesture.removePointer);

    await gesture.moveTo(tester.getCenter(logoFinder));
    await tester.pumpAndSettle();

    expect(find.byIcon(LucideIcons.panelLeftOpen), findsOneWidget);
    final openTooltip = find.text('Open sidebar');
    expect(openTooltip, findsOneWidget);
    expect(tester.getTopLeft(openTooltip).dx, greaterThan(70.0));

    // Clicking the hovered logo triggers onToggle
    await tester.tap(find.byIcon(LucideIcons.panelLeftOpen));
    await tester.pumpAndSettle();
    expect(toggled, isTrue);

    // Hover over the collapsed Projects icon -> tooltip floats to the RIGHT (not covering "+" above)
    final folderCenter = tester.getCenter(folderFinder);
    await gesture.moveTo(folderCenter);
    await tester.pumpAndSettle();

    // Find the visible right-side overlay label (positioned right of the 72px sidebar)
    final projectsTexts = find.text('Projects').evaluate().toList();
    final rightSideTooltip = projectsTexts.where((el) {
      final box = el.renderObject as RenderBox;
      return box.localToGlobal(Offset.zero).dx > 72.0;
    }).toList();
    expect(rightSideTooltip.length, 1);

    final tooltipBox = rightSideTooltip.first.renderObject as RenderBox;
    final tooltipCenterY =
        tooltipBox.localToGlobal(Offset(0, tooltipBox.size.height / 2)).dy;
    // Vertically aligned with the Projects icon, never covering the Plus icon above it
    expect(tooltipCenterY, closeTo(folderCenter.dy, 6.0));
  });

  testWidgets('UnoSidebar toggling collapse smoothly does not throw RenderFlex overflow',
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
    // Pump intermediate frames across the 260ms collapse animation
    for (int i = 0; i < 6; i++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    await tester.pumpAndSettle();

    expect(tester.getSize(find.byType(UnoSidebar)).width, 72.0);
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
    expect(find.text('Ontology Graph'), findsNothing);
    expect(find.byIcon(LucideIcons.boxes), findsNothing);

    // Remaining nav items are displayed (Ontology Graph renamed to Architecture)
    for (final label in [
      'Projects',
      'Overview',
      'Ask AI',
      'Files',
      'Architecture',
      'Ingestion Feed',
      'Archived chats',
    ]) {
      expect(find.text(label), findsOneWidget);
    }

    // Active ('Ask AI') and inactive ('Projects', 'Overview', 'Files', 'Archived chats')
    // icons all align to the exact same X coordinate (36.0)
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
