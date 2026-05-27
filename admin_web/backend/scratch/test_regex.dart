void main() {
  final deadlineStr = '2026-05-27T18:59:00+00:00';
  final regex = RegExp(r'[+-]\d{2}:\d{2}$');
  final matches = regex.hasMatch(deadlineStr);
  print('matches: $matches');
  
  String normalized = deadlineStr;
  if (!normalized.endsWith('Z') && !normalized.contains(regex)) {
    normalized += 'Z';
  }
  print('normalized: $normalized');
}
