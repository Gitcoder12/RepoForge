"""
RepoForge Action Parser V3

Extracts and validates AI generated Forge actions.
"""


import json
import re

from typing import List, Dict, Any



class ActionParser:
    """
    Converts AI responses into safe Forge actions.
    """



    def parse(
        self,
        response: str,
    ) -> List[Dict[str, Any]]:


        actions = []


        for block in self.extract_json(response):

            data = self.safe_json_load(
                block
            )


            if data is None:

                continue



            if isinstance(
                data,
                list
            ):


                for item in data:


                    if self.validate_action(
                        item
                    ):

                        actions.append(
                            item
                        )



            elif isinstance(
                data,
                dict
            ):


                if self.validate_action(
                    data
                ):

                    actions.append(
                        data
                    )



        # Remove duplicate actions

        unique_actions = []

        seen = set()


        for action in actions:


            key = (

                action.get(
                    "type"
                ),

                action.get(
                    "file"
                ),

                action.get(
                    "content"
                )

            )


            if key not in seen:


                seen.add(
                    key
                )


                unique_actions.append(
                    action
                )



        return unique_actions




    def safe_json_load(
        self,
        text: str,
    ):


        try:

            return json.loads(
                text
            )


        except json.JSONDecodeError:


            try:


                fixed = re.sub(

                    r'("content"\s*:\s*")(.*?)(")',

                    lambda match:

                        match.group(1)
                        +
                        match.group(2)
                        .replace(
                            "\n",
                            "\\n"
                        )
                        +
                        match.group(3),

                    text,

                    flags=re.DOTALL

                )


                return json.loads(
                    fixed
                )


            except Exception as error:


                print(
                    "JSON REPAIR FAILED:",
                    error
                )


                return None




    def extract_json(
        self,
        text: str,
    ) -> List[str]:
        """
        Extract JSON arrays/objects from AI output.
        """


        if not isinstance(
            text,
            str
        ):

            return []



        blocks = []



        # Markdown JSON blocks

        matches = re.findall(

            r"```(?:json)?\s*(.*?)```",

            text,

            re.DOTALL | re.IGNORECASE

        )


        blocks.extend(
            matches
        )



        # Raw JSON array

        start = text.find(
            "["
        )


        end = text.rfind(
            "]"
        )


        if start != -1 and end != -1:


            blocks.append(

                text[
                    start:end + 1
                ]

            )



        # Raw JSON object

        start = text.find(
            "{"
        )


        end = text.rfind(
            "}"
        )


        if start != -1 and end != -1:


            blocks.append(

                text[
                    start:end + 1
                ]

            )



        cleaned = []


        for block in blocks:


            block = block.strip()


            if block and block not in cleaned:

                cleaned.append(
                    block
                )



        return cleaned




    def validate_action(
        self,
        action: Dict[str, Any],
    ) -> bool:
        """
        Validate Forge action safety.
        """


        if not isinstance(
            action,
            dict
        ):

            return False



        required = [

            "type",

            "file",

            "content"

        ]



        if not all(

            key in action

            for key in required

        ):

            return False



        if action["type"] not in [

            "create",

            "modify",

            "delete"

        ]:

            return False



        if not isinstance(
            action["file"],
            str
        ):

            return False



        if not isinstance(
            action["content"],
            str
        ):

            return False



        # Security checks

        unsafe = [

            "..",

            "~",

            "/etc",

            "C:\\",

        ]



        for item in unsafe:


            if item in action["file"]:

                return False



        return True