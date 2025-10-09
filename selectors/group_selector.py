"""Group selection functionality for manga chapters."""

from __future__ import annotations




class GroupSelector:
    """Handles group selection logic for manga chapters."""

    def select_group_for_chapter(
        self, available_groups: list[str], chapter_name: str
    ) -> str:
        """
        Select a group for a chapter based on available groups.

        Args:
            available_groups: List of available scanlation groups
            chapter_name: Name of the chapter being processed

        Returns:
            Selected group name

        Raises:
            ValueError: If no groups are available or selection is invalid
        """
        if not available_groups:
            raise ValueError("No groups available for selection")

        # Handle automatic selection when only one group exists
        default_group = self.get_default_group(available_groups)
        if default_group is not None:
            print(f"Using default group '{default_group}' for {chapter_name}")
            return default_group

        # Prompt user for multiple group selection
        return self._prompt_user_for_group(available_groups, chapter_name)

    def get_default_group(self, groups: list[str]) -> str | None:
        """
        Get default group when only one group exists.

        Args:
            groups: List of available groups

        Returns:
            Default group name if only one exists, None otherwise
        """
        if len(groups) == 1:
            return groups[0]
        return None

    def _prompt_user_for_group(
        self, available_groups: list[str], chapter_name: str
    ) -> str:
        """
        Prompt user to select a group from multiple options.

        Args:
            available_groups: List of available groups
            chapter_name: Name of the chapter being processed

        Returns:
            Selected group name

        Raises:
            ValueError: If user selection is invalid
        """
        print(f"\nSelect group for {chapter_name}:")
        for i, group in enumerate(available_groups, 1):
            print(f"  {i}. {group}")

        while True:
            try:
                choice = input("Enter group number: ").strip()
                group_index = int(choice) - 1

                if 0 <= group_index < len(available_groups):
                    selected_group = available_groups[group_index]
                    print(f"Selected group: {selected_group}")
                    return selected_group
                else:
                    print(f"Invalid selection. Please enter a number between 1 and {len(available_groups)}")

            except ValueError:
                print("Invalid input. Please enter a number.")
            except KeyboardInterrupt:
                print("\nOperation cancelled by user.")
                raise ValueError("Group selection cancelled by user")

    def validate_group_selection(self, selected_group: str, available_groups: list[str]) -> bool:
        """
        Validate that the selected group is in the available groups list.

        Args:
            selected_group: The group that was selected
            available_groups: List of available groups

        Returns:
            True if selection is valid, False otherwise
        """
        return selected_group in available_groups