enum CheckStatus {
  pending,
  checking,
  passed,
  failed,
  warning;

  bool get isPassed => this == CheckStatus.passed;
  bool get isFailed => this == CheckStatus.failed;
  bool get isChecking => this == CheckStatus.checking;
}

class CheckItem {
  final String id;
  final String title;
  final String description;
  final CheckStatus status;
  final String? failureMessage;
  final String? remediationHint;
  final String? technicalDetails;

  const CheckItem({
    required this.id,
    required this.title,
    required this.description,
    this.status = CheckStatus.pending,
    this.failureMessage,
    this.remediationHint,
    this.technicalDetails,
  });

  CheckItem copyWith({
    String? id,
    String? title,
    String? description,
    CheckStatus? status,
    String? failureMessage,
    String? remediationHint,
    String? technicalDetails,
  }) {
    return CheckItem(
      id: id ?? this.id,
      title: title ?? this.title,
      description: description ?? this.description,
      status: status ?? this.status,
      failureMessage: failureMessage ?? this.failureMessage,
      remediationHint: remediationHint ?? this.remediationHint,
      technicalDetails: technicalDetails ?? this.technicalDetails,
    );
  }
}
