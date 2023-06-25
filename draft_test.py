from Leaders import TYPES_OF_CIV
from Modules.Draft import DraftModule

class NotACPLBot: 
    def __init__(self):
        self.database = None

draftModule = DraftModule(client=NotACPLBot())

for i in range(2,16):
    print('validating draft of size ' + str(i))
    drafts = draftModule.get_raw_draft(10,  '.vietnam.trajan.khmer.kupe')
    # This code verifies that no draft has more than 2 of a type compared to the other drafts.
    all_types_about_the_same = True
    for civ_type in TYPES_OF_CIV:
        numberOfThisType = len([civ for civ in drafts[0] if civ.type_of_civ == civ_type])
        for draft in drafts:
             types_about_the_same = 2 >= abs(numberOfThisType - len([civ for civ in draft if civ.type_of_civ == civ_type]))
             if not types_about_the_same:
                  all_types_about_the_same = False
      
    # This code verifies that no draft has more civs than another draft. 
    size_the_draft_should_be = len(drafts[0])
    size_valid = True
    for	draft in drafts:
        if(len(draft) != size_the_draft_should_be):
                size_valid = False
                
    print(str(size_valid) + ' ' + str(types_about_the_same))
    if not size_valid or not types_about_the_same:
        for draft in drafts:
            draft.sort(key=lambda civ: civ.type_of_civ)
            print('\n'.join([civ.civ + '|' + civ.type_of_civ for civ in draft]))
            print('-------------------')


